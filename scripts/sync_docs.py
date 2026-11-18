#!/usr/bin/env python3
"""Sync Anthropic English documentation sites into a local/Git mirror.

Four-stage pipeline:
1. Metadata Fetch: download llms.txt and sitemap.xml per site into _meta/https_<site>/.
2. Reconcile: normalize URLs from both sources, emit reconcile_report.json, and build tasks.
3. Incremental Sync: skip unchanged pages via sitemap lastmod (unless --full),
   validate markdown payloads, write files safely, and clean stale manifest files.
4. Index & Summary: write <output_dir>_llms.local.md at repo root, save manifest.json
   under _meta/<output_dir>/, and emit summary.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import re
import sys
import threading
import time
from typing import Any
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests


LOGGER = logging.getLogger("sync_docs")

REPO_ROOT = Path(__file__).resolve().parent.parent
META_ROOT = REPO_ROOT / "_meta"

DEFAULT_USER_AGENT = "claude-doc-sync/1.0 (+https://github.com)"
DEFAULT_TIMEOUT = 30
DEFAULT_DELAY = 0.3
MAX_RETRIES = 3
NON_DOC_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".pdf",
        ".xml",
        ".json",
        ".yaml",
        ".yml",
        ".txt",
        ".zip",
    }
)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
LLMS_URL_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


@dataclass(frozen=True)
class SiteConfig:
    """Configuration for one Anthropic documentation site."""

    key: str
    llms_url: str
    sitemap_url: str
    base_prefix: str
    output_dir: str


SITES: dict[str, SiteConfig] = {
    "claude.com_docs": SiteConfig(
        key="claude.com_docs",
        llms_url="https://claude.com/docs/llms.txt",
        sitemap_url="https://claude.com/docs/sitemap.xml",
        base_prefix="https://claude.com/docs/",
        output_dir="https_claude.com_docs",
    ),
    "code.claude.com_docs": SiteConfig(
        key="code.claude.com_docs",
        llms_url="https://code.claude.com/docs/llms.txt",
        sitemap_url="https://code.claude.com/docs/sitemap.xml",
        base_prefix="https://code.claude.com/docs/en/",
        output_dir="https_code.claude.com_docs",
    ),
    "platform.claude.com": SiteConfig(
        key="platform.claude.com",
        llms_url="https://platform.claude.com/llms.txt",
        sitemap_url="https://platform.claude.com/sitemap.xml",
        base_prefix="https://platform.claude.com/docs/en/",
        output_dir="https_platform.claude.com_docs",
    ),
}


@dataclass
class DocTask:
    """Normalized page sync task."""

    key: str
    url: str
    rel_path: str
    lastmod: str | None
    source: str  # "both" | "only_in_llms" | "only_in_sitemap"


@dataclass
class SiteStats:
    """Per-site execution summary."""

    site: str
    llms_count: int = 0
    sitemap_count: int = 0
    merged_count: int = 0
    selected_count: int = 0
    added: int = 0
    updated: int = 0
    skipped_lastmod: int = 0
    unchanged_304: int = 0
    unchanged_hash: int = 0
    deleted: int = 0
    failed: int = 0
    failed_pages: list[dict[str, str]] | None = None
    fatal_error: str | None = None

    def __post_init__(self) -> None:
        if self.failed_pages is None:
            self.failed_pages = []


class RateLimiter:
    """Thread-safe minimum-interval rate limiter."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = max(0.0, min_interval)
        self._lock = threading.Lock()
        self._last_request = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request = time.monotonic()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/markdown, text/plain, application/xml, text/xml;q=0.9, */*;q=0.8",
        }
    )
    return session


def parse_retry_after(header_val: str | None) -> float | None:
    if not header_val:
        return None
    try:
        seconds = float(header_val.strip())
        return min(max(seconds, 1.0), 60.0)
    except ValueError:
        return None


def http_get_with_retry(
    session: requests.Session,
    url: str,
    limiter: RateLimiter,
    extra_headers: dict[str, str] | None = None,
) -> requests.Response:
    """Perform GET with rate limiting, 429 Retry-After, and exponential backoff."""
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        limiter.wait()
        try:
            resp = session.get(url, headers=extra_headers, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= MAX_RETRIES:
                raise
            delay = min(2.0 * (2**attempt), 30.0) + random.uniform(0.0, 0.5)
            LOGGER.warning("Request error for %s (%s); retrying in %.1fs", url, exc, delay)
            time.sleep(delay)
            continue

        if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
            retry_after = parse_retry_after(resp.headers.get("Retry-After"))
            delay = retry_after if retry_after is not None else min(2.0 * (2**attempt), 30.0)
            delay += random.uniform(0.0, 0.5)
            LOGGER.warning("HTTP %s for %s; retrying in %.1fs", resp.status_code, url, delay)
            time.sleep(delay)
            continue

        return resp

    assert last_exc is not None
    raise last_exc


def normalize_doc_key(raw_rel: str) -> str:
    """Normalize a relative doc path into a canonical comparison key."""
    path = raw_rel.strip().strip("/")
    for suffix in (".md", ".html"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    path = path.strip("/")
    if not path or path == "index":
        return "index"
    if path.endswith("/index"):
        return path[: -len("/index")]
    return path


def extract_relative_from_prefix(url: str, base_prefix: str) -> str | None:
    """Return path relative to base_prefix, or None if URL is outside prefix."""
    clean_url = url.split("#", 1)[0].split("?", 1)[0]
    prefix_no_slash = base_prefix.rstrip("/")
    url_no_slash = clean_url.rstrip("/")

    if url_no_slash == prefix_no_slash:
        return ""
    if clean_url.startswith(base_prefix):
        return clean_url[len(base_prefix) :]
    return None


def parse_llms_links(llms_text: str, site: SiteConfig) -> dict[str, tuple[str, str]]:
    """Extract {normalized_key: (url, rel_path)} from llms.txt."""
    found: dict[str, tuple[str, str]] = {}
    for match in LLMS_URL_RE.finditer(llms_text):
        url = match.group(1).strip()
        rel = extract_relative_from_prefix(url, site.base_prefix)
        if rel is None:
            continue
        rel_clean = rel.lstrip("/")
        if not rel_clean.endswith(".md"):
            continue
        key = normalize_doc_key(rel_clean)
        found.setdefault(key, (url, rel_clean))
    return found


def safe_parse_xml(xml_bytes: bytes) -> ET.Element:
    """Parse XML safely, disabling external entities and DTDs when supported."""
    try:
        parser = ET.XMLParser(forbid_dtd=True, forbid_entities=True, forbid_external=True)
        return ET.fromstring(xml_bytes, parser=parser)
    except TypeError:
        return ET.fromstring(xml_bytes)


def parse_sitemap_entries(xml_bytes: bytes, site: SiteConfig) -> dict[str, str | None]:
    """Extract {normalized_key: lastmod} from sitemap.xml."""
    root = safe_parse_xml(xml_bytes)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    url_nodes = root.findall(".//sm:url", ns)
    use_ns = bool(url_nodes)
    if not url_nodes:
        url_nodes = root.findall(".//url")

    entries: dict[str, str | None] = {}
    for node in url_nodes:
        loc_node = node.find("sm:loc", ns) if use_ns else node.find("loc")
        if loc_node is None or not loc_node.text:
            continue
        loc = loc_node.text.strip()

        rel = extract_relative_from_prefix(loc, site.base_prefix)
        if rel is None:
            continue

        parsed_path = urlparse(loc).path.lower()
        if any(parsed_path.endswith(ext) for ext in NON_DOC_EXTENSIONS):
            continue

        lastmod_node = node.find("sm:lastmod", ns) if use_ns else node.find("lastmod")
        lastmod = lastmod_node.text.strip() if lastmod_node is not None and lastmod_node.text else None

        key = normalize_doc_key(rel)
        # Keep the first non-None lastmod if duplicate keys exist
        if key not in entries or (entries[key] is None and lastmod is not None):
            entries[key] = lastmod

    return entries


def build_tasks_and_report(
    site: SiteConfig,
    llms_map: dict[str, tuple[str, str]],
    sitemap_map: dict[str, str | None],
) -> tuple[list[DocTask], dict[str, Any]]:
    """Reconcile llms.txt and sitemap.xml into ordered DocTasks + report dict."""
    llms_keys = set(llms_map.keys())
    sitemap_keys = set(sitemap_map.keys())
    all_keys = sorted(llms_keys | sitemap_keys)

    only_in_llms = sorted(llms_keys - sitemap_keys)
    only_in_sitemap = sorted(sitemap_keys - llms_keys)
    both = sorted(llms_keys & sitemap_keys)

    tasks: list[DocTask] = []
    for key in all_keys:
        if key in llms_map:
            url, rel_path = llms_map[key]
            source = "both" if key in sitemap_map else "only_in_llms"
        else:
            rel_path = "index.md" if key == "index" else f"{key}.md"
            url = f"{site.base_prefix}{rel_path}"
            source = "only_in_sitemap"

        tasks.append(
            DocTask(
                key=key,
                url=url,
                rel_path=rel_path,
                lastmod=sitemap_map.get(key),
                source=source,
            )
        )

    report = {
        "site": site.key,
        "generated_at": utc_now_iso(),
        "counts": {
            "llms": len(llms_keys),
            "sitemap": len(sitemap_keys),
            "merged": len(all_keys),
            "both": len(both),
            "only_in_llms": len(only_in_llms),
            "only_in_sitemap": len(only_in_sitemap),
        },
        "only_in_llms": only_in_llms,
        "only_in_sitemap": only_in_sitemap,
    }
    return tasks, report


def validate_markdown(resp: requests.Response) -> str:
    """Validate HTTP status and ensure response payload is valid non-HTML markdown."""
    if resp.status_code != 200:
        raise ValueError(f"HTTP {resp.status_code}")

    content_type = (resp.headers.get("Content-Type") or "").lower()
    text = resp.text
    stripped = text.lstrip()
    if not stripped:
        raise ValueError("Empty response body")

    head = stripped[:200].lower()
    if head.startswith("<!doctype") or head.startswith("<html"):
        raise ValueError("Received HTML instead of markdown")
    if "text/html" in content_type and "<html" in stripped[:1000].lower():
        raise ValueError(f"HTML Content-Type ({content_type})")

    return text


def safe_target_path(output_dir: Path, rel_path: str) -> Path:
    """Resolve rel_path safely inside output_dir, rejecting path traversal."""
    target = (output_dir / rel_path).resolve()
    root_resolved = output_dir.resolve()
    if target == root_resolved or root_resolved not in target.parents:
        raise ValueError(f"Unsafe relative path: {rel_path}")
    return target


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("files"), dict):
                return data
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Could not read manifest %s (%s); starting fresh", manifest_path, exc)
    return {"files": {}}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sync_single_task(
    task: DocTask,
    output_dir: Path,
    prev_entry: dict[str, Any] | None,
    full: bool,
    limiter: RateLimiter,
    thread_local: threading.local,
) -> tuple[str, dict[str, Any] | None, dict[str, str] | None]:
    """Sync one page. Returns (outcome, new_manifest_entry, failure_info)."""
    target_path = safe_target_path(output_dir, task.rel_path)
    file_exists = target_path.is_file()

    if (
        not full
        and file_exists
        and prev_entry is not None
        and task.lastmod is not None
        and prev_entry.get("lastmod") == task.lastmod
    ):
        return "skipped_lastmod", prev_entry, None

    session = getattr(thread_local, "session", None)
    if session is None:
        session = make_session()
        thread_local.session = session

    extra_headers: dict[str, str] = {}
    if not full and file_exists and prev_entry is not None:
        if prev_entry.get("etag"):
            extra_headers["If-None-Match"] = str(prev_entry["etag"])
        if prev_entry.get("last_modified"):
            extra_headers["If-Modified-Since"] = str(prev_entry["last_modified"])

    try:
        resp = http_get_with_retry(session, task.url, limiter, extra_headers or None)
        if resp.status_code == 304 and file_exists and prev_entry is not None:
            updated_entry = dict(prev_entry)
            updated_entry["lastmod"] = task.lastmod
            updated_entry["synced_at"] = utc_now_iso()
            return "unchanged_304", updated_entry, None

        text = validate_markdown(resp)
    except Exception as exc:  # noqa: BLE001 - per-page isolation
        return "failed", prev_entry, {"path": task.rel_path, "url": task.url, "error": str(exc)}

    new_hash = sha256_text(text)
    if file_exists and prev_entry is not None and prev_entry.get("sha256") == new_hash:
        outcome = "unchanged_hash"
    else:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(text, encoding="utf-8", newline="\n")
        outcome = "updated" if file_exists else "added"

    entry = {
        "url": task.url,
        "source": task.source,
        "lastmod": task.lastmod,
        "sha256": new_hash,
        "bytes": len(text.encode("utf-8")),
        "etag": resp.headers.get("ETag"),
        "last_modified": resp.headers.get("Last-Modified"),
        "synced_at": utc_now_iso(),
    }
    return outcome, entry, None


def cleanup_stale_files(
    output_dir: Path,
    prev_files: dict[str, Any],
    desired_rel_paths: set[str],
) -> int:
    """Remove files tracked in previous manifest that are absent from current tasks."""
    deleted = 0
    for old_rel in sorted(set(prev_files.keys()) - desired_rel_paths):
        try:
            target = safe_target_path(output_dir, old_rel)
        except ValueError:
            continue
        if target.is_file():
            target.unlink()
            deleted += 1
            prune_empty_parents(target.parent, stop_at=output_dir)
    return deleted


def prune_empty_parents(directory: Path, stop_at: Path) -> None:
    root_resolved = stop_at.resolve()
    current = directory.resolve()
    while current != root_resolved and root_resolved in current.parents:
        try:
            next(current.iterdir())
            break
        except StopIteration:
            current.rmdir()
            current = current.parent


def write_local_index(site: SiteConfig, llms_text: str) -> None:
    """Write <output_dir>_llms.local.md at repo root with repo-root-relative paths."""
    local_index = llms_text.replace(site.base_prefix, f"{site.output_dir}/")
    index_path = REPO_ROOT / f"{site.output_dir}_llms.local.md"
    index_path.write_text(local_index, encoding="utf-8", newline="\n")


def process_site(
    site: SiteConfig,
    full: bool,
    limit: int,
    dry_run: bool,
    workers: int,
    limiter: RateLimiter,
) -> SiteStats:
    """Run all 4 stages for a single site."""
    stats = SiteStats(site=site.key)
    site_meta_dir = META_ROOT / site.output_dir
    output_dir = REPO_ROOT / site.output_dir
    site_meta_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    LOGGER.info("[%s] Stage 1: Fetching llms.txt & sitemap.xml", site.key)
    try:
        llms_resp = http_get_with_retry(session, site.llms_url, limiter)
        if llms_resp.status_code != 200 or not llms_resp.text.strip():
            raise RuntimeError(f"llms.txt HTTP {llms_resp.status_code}")
        llms_text = llms_resp.text

        sitemap_resp = http_get_with_retry(session, site.sitemap_url, limiter)
        if sitemap_resp.status_code != 200 or not sitemap_resp.content.strip():
            raise RuntimeError(f"sitemap.xml HTTP {sitemap_resp.status_code}")
        sitemap_bytes = sitemap_resp.content
    except Exception as exc:  # noqa: BLE001
        stats.fatal_error = f"Metadata fetch failed: {exc}"
        LOGGER.error("[%s] %s", site.key, stats.fatal_error)
        return stats

    (site_meta_dir / "llms.txt").write_text(llms_text, encoding="utf-8", newline="\n")
    (site_meta_dir / "sitemap.xml").write_bytes(sitemap_bytes)

    LOGGER.info("[%s] Stage 2: Reconciling URLs", site.key)
    try:
        llms_map = parse_llms_links(llms_text, site)
        sitemap_map = parse_sitemap_entries(sitemap_bytes, site)
        tasks, report = build_tasks_and_report(site, llms_map, sitemap_map)
    except Exception as exc:  # noqa: BLE001
        stats.fatal_error = f"Reconcile failed: {exc}"
        LOGGER.error("[%s] %s", site.key, stats.fatal_error)
        return stats

    write_json(site_meta_dir / "reconcile_report.json", report)
    stats.llms_count = report["counts"]["llms"]
    stats.sitemap_count = report["counts"]["sitemap"]
    stats.merged_count = report["counts"]["merged"]

    selected_tasks = tasks[:limit] if limit > 0 else tasks
    stats.selected_count = len(selected_tasks)
    LOGGER.info(
        "[%s] Reconciled: llms=%d sitemap=%d merged=%d (only_llms=%d, only_sitemap=%d), selected=%d",
        site.key,
        stats.llms_count,
        stats.sitemap_count,
        stats.merged_count,
        report["counts"]["only_in_llms"],
        report["counts"]["only_in_sitemap"],
        stats.selected_count,
    )

    if dry_run:
        return stats

    manifest_path = site_meta_dir / "manifest.json"
    prev_manifest = load_manifest(manifest_path)
    prev_files: dict[str, Any] = prev_manifest.get("files", {})
    new_files: dict[str, Any] = dict(prev_files) if limit > 0 else {}

    LOGGER.info("[%s] Stage 3: Syncing %d pages (full=%s, workers=%d)", site.key, len(selected_tasks), full, workers)
    thread_local = threading.local()

    def run_one(t: DocTask) -> tuple[DocTask, str, dict[str, Any] | None, dict[str, str] | None]:
        outcome, entry, err = sync_single_task(
            task=t,
            output_dir=output_dir,
            prev_entry=prev_files.get(t.rel_path),
            full=full,
            limiter=limiter,
            thread_local=thread_local,
        )
        return t, outcome, entry, err

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(run_one, task) for task in selected_tasks]
        for fut in as_completed(futures):
            task, outcome, entry, err = fut.result()
            if outcome == "added":
                stats.added += 1
            elif outcome == "updated":
                stats.updated += 1
            elif outcome == "skipped_lastmod":
                stats.skipped_lastmod += 1
            elif outcome == "unchanged_304":
                stats.unchanged_304 += 1
            elif outcome == "unchanged_hash":
                stats.unchanged_hash += 1
            elif outcome == "failed":
                stats.failed += 1
                if err is not None:
                    stats.failed_pages.append(err)
                    LOGGER.warning("[%s] Failed %s: %s", site.key, err["path"], err["error"])

            if entry is not None:
                new_files[task.rel_path] = entry

    # Only prune deleted files on full-list runs (not --limit) when at least one page succeeded or skipped
    if limit == 0 and selected_tasks and stats.failed < len(selected_tasks):
        desired = {t.rel_path for t in selected_tasks}
        stats.deleted = cleanup_stale_files(output_dir, prev_files, desired)

    LOGGER.info("[%s] Stage 4: Updating local index & manifest", site.key)
    write_local_index(site, llms_text)
    manifest_payload = {
        "site": site.key,
        "base_prefix": site.base_prefix,
        "output_dir": site.output_dir,
        "updated_at": utc_now_iso(),
        "partial_limit": limit if limit > 0 else None,
        "failed_pages": stats.failed_pages,
        "files": dict(sorted(new_files.items())),
    }
    write_json(manifest_path, manifest_payload)

    if selected_tasks and stats.failed == len(selected_tasks):
        stats.fatal_error = "All selected pages failed to fetch"

    return stats


def format_markdown_summary(all_stats: list[SiteStats], dry_run: bool, limit: int, full: bool) -> str:
    mode_bits = ["dry-run" if dry_run else ("full" if full else "incremental")]
    if limit > 0:
        mode_bits.append(f"limit={limit}")
    lines = [
        f"## Claude Docs Sync Summary ({', '.join(mode_bits)})",
        "",
        "| Site | llms | sitemap | merged | selected | added | updated | skipped | unchanged | deleted | failed |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in all_stats:
        unchanged = s.unchanged_304 + s.unchanged_hash
        status_note = " (FATAL)" if s.fatal_error else ""
        lines.append(
            f"| `{s.site}`{status_note} | {s.llms_count} | {s.sitemap_count} | {s.merged_count} | "
            f"{s.selected_count} | {s.added} | {s.updated} | {s.skipped_lastmod} | "
            f"{unchanged} | {s.deleted} | {s.failed} |"
        )

    failures = [(s.site, item) for s in all_stats for item in (s.failed_pages or [])]
    if failures:
        lines.extend(["", "### Failed Pages (first 30)"])
        for site_key, item in failures[:30]:
            lines.append(f"- `{site_key}` `{item['path']}`: {item['error']}")

    fatals = [s for s in all_stats if s.fatal_error]
    if fatals:
        lines.extend(["", "### Fatal Errors"])
        for s in fatals:
            lines.append(f"- `{s.site}`: {s.fatal_error}")

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Anthropic English documentation.")
    parser.add_argument(
        "--site",
        action="append",
        choices=["all", *SITES.keys()],
        help="Target site(s) to sync (default: all). May be repeated.",
    )
    parser.add_argument("--full", action="store_true", help="Ignore lastmod cache and verify SHA-256 of all pages.")
    parser.add_argument("--limit", type=int, default=0, help="Sync at most N pages per site (0 = no limit).")
    parser.add_argument("--dry-run", action="store_true", help="Run Stage 1 & 2 only (metadata + reconcile).")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent download workers per site (default: 1).")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Minimum delay in seconds between HTTP requests.")
    parser.add_argument("--summary-file", type=Path, help="Write Markdown summary to this file.")
    parser.add_argument("--metrics-file", type=Path, help="Write aggregate sync counts as JSON to this file.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.limit < 0:
        LOGGER.error("--limit must be >= 0")
        return 2

    if not args.site or "all" in args.site:
        selected_sites = list(SITES.values())
    else:
        seen: set[str] = set()
        selected_sites = []
        for key in args.site:
            if key not in seen:
                seen.add(key)
                selected_sites.append(SITES[key])

    limiter = RateLimiter(args.delay)
    all_stats: list[SiteStats] = []
    for site in selected_sites:
        all_stats.append(
            process_site(
                site=site,
                full=args.full,
                limit=args.limit,
                dry_run=args.dry_run,
                workers=args.workers,
                limiter=limiter,
            )
        )

    summary_md = format_markdown_summary(all_stats, dry_run=args.dry_run, limit=args.limit, full=args.full)
    print("\n" + summary_md)

    if args.summary_file:
        args.summary_file.parent.mkdir(parents=True, exist_ok=True)
        args.summary_file.write_text(summary_md, encoding="utf-8")

    if args.metrics_file:
        metrics = {
            "added": sum(s.added for s in all_stats),
            "updated": sum(s.updated for s in all_stats),
            "deleted": sum(s.deleted for s in all_stats),
            "unchanged": sum(s.skipped_lastmod + s.unchanged_304 + s.unchanged_hash for s in all_stats),
            "failed": sum(s.failed for s in all_stats),
        }
        write_json(args.metrics_file, metrics)

    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        with open(gh_summary, "a", encoding="utf-8") as fh:
            fh.write(summary_md)

    if any(s.fatal_error for s in all_stats):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
