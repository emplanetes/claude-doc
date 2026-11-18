# claude-doc

[简体中文](README.md) | **English**

A **read-only local/Git mirror of Anthropic's official English documentation**, optimized for high-precision AI Agent retrieval and offline search. Maintained automatically via a single configurable Python script (`scripts/sync_docs.py`) and GitHub Actions.

---

## Core Positioning & Design Principles

- **Complete English Official Coverage**: Mirrors the raw English Markdown (`*.md`) pages across Anthropic's three official documentation sites (`claude.com/docs`, `code.claude.com/docs`, and `platform.claude.com`).
- **Preserves Nested Directory Hierarchy**: Keeps the original URL path structure (e.g., `https_platform.claude.com_docs/api/...`) instead of flattening filenames. This avoids single-directory listing truncation and keeps semantic paths intact for `glob` and `rg` search.
- **Zero-LLM Indexing**: Uses each site's native `llms.txt` together with deterministically rewritten root `*_llms.local.md` files—zero token cost and zero hallucination risk.
- **English-Only (Signal over Noise)**: Excludes non-English localized routes (which are partial subsets on some sites, ~342 pages) to ensure complete coverage without duplicate search noise.
- **Unified Source Model**: Relies strictly on each site's official `llms.txt` and `sitemap.xml`, reconciled on every run.

---

## Mirrored Sites & Local Directory Mapping

| Official Site | Local Docs Directory (`.md` only) | Root Local Index | Metadata Directory | Sample Baseline Count (`llms` / `sitemap`) | Coverage |
| :--- | :--- | :--- | :--- | :---: | :--- |
| [https://claude.com/docs](https://claude.com/docs) | [`https_claude.com_docs/`](https_claude.com_docs/) | [`https_claude.com_docs_llms.local.md`](https_claude.com_docs_llms.local.md) | [`_meta/https_claude.com_docs/`](_meta/https_claude.com_docs/) | 291 / 291 | Claude.ai, Cowork, Connectors, MCP Apps, Plugins, Desktop 3P, Claude Tag, Government, Claude Science |
| [https://code.claude.com/docs](https://code.claude.com/docs) | [`https_code.claude.com_docs/`](https_code.claude.com_docs/) | [`https_code.claude.com_docs_llms.local.md`](https_code.claude.com_docs_llms.local.md) | [`_meta/https_code.claude.com_docs/`](_meta/https_code.claude.com_docs/) | 205 / 204 | Claude Code CLI, IDE, Hooks, MCP, Subagents, Plugins, Agent SDK, Enterprise Admin (incl. `claude-tag.md`) |
| [https://platform.claude.com](https://platform.claude.com) | [`https_platform.claude.com_docs/`](https_platform.claude.com_docs/) | [`https_platform.claude.com_docs_llms.local.md`](https_platform.claude.com_docs_llms.local.md) | [`_meta/https_platform.claude.com_docs/`](_meta/https_platform.claude.com_docs/) | 923 / 923 | Messages API, API Reference, Managed Agents, Tool Use, Models & Pricing, Client SDKs |

> Note: Baseline counts reflect initial research; actual counts track live updates on Anthropic's sites and are recorded in each site's `_meta/*/reconcile_report.json`.

---

## Repository Layout

```text
claude-doc/
├── .github/
│   └── workflows/
│       └── sync-docs.yml                       # Scheduled & manual GitHub Actions workflow
├── _meta/                                      # Metadata, index backups & sync state (auto-managed)
│   ├── https_claude.com_docs/
│   │   ├── llms.txt                            # Upstream llms.txt backup
│   │   ├── sitemap.xml                         # Upstream sitemap.xml backup
│   │   ├── reconcile_report.json               # llms.txt vs sitemap.xml reconciliation report
│   │   └── manifest.json                       # Per-file URL, lastmod, sha256 & sync status
│   ├── https_code.claude.com_docs/
│   │   └── ...
│   └── https_platform.claude.com_docs/
│       └── ...
├── https_claude.com_docs/                      # claude.com/docs Markdown mirror (pure .md tree)
├── https_code.claude.com_docs/                 # code.claude.com/docs/en Markdown mirror (pure .md tree)
├── https_platform.claude.com_docs/             # platform.claude.com/docs/en Markdown mirror (pure .md tree)
├── https_claude.com_docs_llms.local.md         # Local path index for claude.com/docs (repo-root relative)
├── https_code.claude.com_docs_llms.local.md    # Local path index for code.claude.com/docs (repo-root relative)
├── https_platform.claude.com_docs_llms.local.md # Local path index for platform.claude.com (repo-root relative)
├── scripts/
│   ├── sync_docs.py                            # Unified 4-stage sync script
│   └── requirements.txt                        # Python dependencies
├── .gitignore
├── AGENT.md                                    # Retrieval instructions for AI Agents
├── LICENSE                                     # MIT License (with scope note for mirrored content)
├── README.md                                   # Chinese documentation
└── README_EN.md                                # English documentation
```

---

## Getting the Repository

### Option 1: Git Clone (Recommended for easy updates)

```bash
# Full clone (includes full commit history)
git clone https://github.com/emplanetes/claude-doc.git

# Shallow clone (latest snapshot only, faster download and smaller disk footprint)
git clone --depth 1 https://github.com/emplanetes/claude-doc.git
```

To pull future monthly documentation updates into your local copy:

```bash
cd claude-doc
git pull
```

### Option 2: Download ZIP Archive (No Git required)

1. Open the repository homepage: [https://github.com/emplanetes/claude-doc](https://github.com/emplanetes/claude-doc)
2. Click **`<> Code`** -> **`Download ZIP`** (or download directly: [claude-doc-main.zip](https://github.com/emplanetes/claude-doc/archive/refs/heads/main.zip))
3. Extract the archive locally and browse it with your Markdown reader or AI Agent.

---

## Using with AI Agents

After cloning or attaching this repository to your AI Agent workspace, use the following retrieval flow (see [AGENT.md](AGENT.md)):

1. **Start with root `*_llms.local.md` indexes**
   Each site has a corresponding `*_llms.local.md` at the repository root where documentation URLs are rewritten to **repository-root-relative paths** (e.g., `https_platform.claude.com_docs/agents-and-tools/tool-use/bash-tool.md`), allowing Agents to open target files directly.
2. **Use `glob` / `rg` across `https_*_docs/`**
   The three content directories contain only Markdown documentation files with zero index clutter, making keyword searches fast and clean.
3. **Verify freshness when needed**
   Check `_meta/<site_dir>/manifest.json` (`updated_at`, `lastmod`, `sha256`, `failed_pages`) and `reconcile_report.json` to inspect the latest sync state.

---

## Local Reading Tip

If you want to browse these `.md` files locally with clean web-style rendering, we recommend using a **Chromium-based browser (Chrome, Edge, etc.)** with the **[Markdown Reader](https://md-reader.github.io/)** extension (opening a root `*_llms.local.md` index lets you click straight through to local docs):

- Homepage: https://md-reader.github.io/
- Chrome Web Store: [Markdown Reader](https://chromewebstore.google.com/detail/markdown-reader/medapdbncneneejhbgcjceippjlfkmkg)
- Microsoft Edge Addons: [Markdown Reader](https://microsoftedge.microsoft.com/addons/detail/markdown-reader/djnplooklihmkcioemdjfcednfkpiodc)

> Tip: After installing the extension, enable **"Allow access to file URLs"** in your browser's extension settings so it can render local `file://` Markdown files and relative links directly.

---

## How the Sync Pipeline Works (`scripts/sync_docs.py`)

Built on a **1-engine + 3-site-config** architecture running four stages:

1. **Stage 1: Metadata Fetch**
   Downloads `llms.txt` and `sitemap.xml` per site into `_meta/<site_dir>/`, safely parsing XML (disabling DTDs/external entities when supported) to extract `<loc>` and `<lastmod>`.
2. **Stage 2: Cross-Source Reconcile**
   - Filters out non-English locales (e.g., `/docs/zh-CN/`), `/_llms/*.txt` language indexes, console web routes, and non-doc assets;
   - Normalizes paths and directory index pages (`index`, `.../index.md`);
   - Writes `reconcile_report.json` (`only_in_llms`, `only_in_sitemap`) and builds the unified task list.
3. **Stage 3: Validation, Sync & Safe Cleanup**
   - **Incremental vs. Full Mode**: In incremental mode, pages with an existing local file and matching `<lastmod>` in `manifest.json` are skipped without HTTP requests (note: `platform.claude.com`'s `sitemap.xml` omits `<lastmod>`, so it falls back to SHA-256 comparison). Passing `--full` bypasses `lastmod` and verifies SHA-256 across all pages.
   - **Rate Limiting & Resilience**: Configurable `--workers` and `--delay`; honors `HTTP 429 Retry-After` and applies exponential backoff on transient network/TLS errors. Individual page failures are recorded in `failed_pages` without overwriting existing local files or aborting other pages.
   - **Payload Validation**: Enforces HTTP 200, non-empty body, and rejects HTML responses (`<!DOCTYPE` / `<html`) so error pages are never saved as `.md`.
   - **Safe Stale Cleanup**: On full-list runs (without `--limit`), removes obsolete `.md` files tracked in the previous `manifest.json` and prunes empty parent directories without touching untracked files.
4. **Stage 4: Index & Summary**
   Writes `*_llms.local.md` at the repo root, updates `_meta/<site_dir>/manifest.json`, prints the summary table, and appends it to `$GITHUB_STEP_SUMMARY` when running in GitHub Actions.

---

## Local Usage

### Prerequisites

- Python 3.11+ (tested on Python 3.13)
- Install dependencies:

```bash
pip install -r scripts/requirements.txt
```

### Common Commands

```bash
# 1. Fetch metadata & reconcile only (no .md downloads)
python scripts/sync_docs.py --dry-run

# 2. Full sync across all 3 sites (SHA-256 check on all pages)
python scripts/sync_docs.py --full --workers 2

# 3. Incremental sync (skip pages with unchanged sitemap lastmod)
python scripts/sync_docs.py --workers 2

# 4. Sync a single site (claude.com_docs / code.claude.com_docs / platform.claude.com)
python scripts/sync_docs.py --site code.claude.com_docs --full

# 5. Small-batch test (first 15 pages per site; skips stale cleanup)
python scripts/sync_docs.py --limit 15
```

### CLI Options

| Option | Description | Default |
| :--- | :--- | :--- |
| `--site` | Target site(s), repeatable (`all`, `claude.com_docs`, `code.claude.com_docs`, `platform.claude.com`) | `all` |
| `--full` | Ignore `lastmod` cache and verify SHA-256 of all pages | `false` |
| `--limit N` | Sync at most `N` pages per site (`0` = unlimited; `> 0` disables stale-file pruning) | `0` |
| `--dry-run` | Run Stage 1 & 2 only (metadata fetch + `reconcile_report.json`) | `false` |
| `--workers N` | Concurrent download workers per site | `1` |
| `--delay S` | Minimum delay in seconds between HTTP requests | `0.3` |
| `--summary-file PATH` | Write Markdown summary to a file | None |
| `--metrics-file PATH` | Write aggregate counts (`added`, `updated`, `deleted`, `unchanged`, `failed`) as JSON | None |
| `--verbose` | Enable debug logging | `false` |

---

## GitHub Actions Automation

Configured in [`.github/workflows/sync-docs.yml`](.github/workflows/sync-docs.yml):

- **Monthly Schedule**: Runs on the **15th of every month at 00:00 UTC (08:00 Beijing Time)** (`cron: '0 0 15 * *'`) with full verification (`--full --workers 2`).
- **Manual Dispatch (`workflow_dispatch`)**: Trigger anytime from the Actions tab with:
  - `full_sync`: Force full SHA-256 verification (default `true`)
  - `site`: Target `all` or an individual site (default `all`)
- **Permissions & Concurrency**: Grants `permissions: contents: write` for automated pushes and uses `concurrency` to serialize overlapping runs.
- **Two-Batch Commit Strategy** (distinguishes manual vs. scheduled runs; skips doc commits when 0 docs changed):
  1. **Documentation & root local indexes** (`https_*` and `*_llms.local.md`, committed only when changed):
     - Manual: `文档手动更新：新增X 修改Y 删除Z 不变W`
     - Scheduled: `文档常规更新：新增X 修改Y 删除Z 不变W`
  2. **Metadata & reconcile reports** (`_meta/`):
     - Manual: `元数据手动更新（文档有变化）` / `元数据手动更新（无文档变更）`
     - Scheduled: `元数据常规检查（文档有变化）` / `元数据常规检查（无文档变更）`

---

## License & Disclaimer

- The synchronization scripts, workflow configuration, and supporting files in this repository are licensed under the [MIT License](LICENSE) (Copyright (c) 2026 Roy Woo).
- All mirrored documentation content belongs to **Anthropic** and is subject to Anthropic's Terms of Service.
- This repository is provided for technical reference, archival, and AI Agent local retrieval; please refer to Anthropic's official documentation sites for the latest authoritative information.
