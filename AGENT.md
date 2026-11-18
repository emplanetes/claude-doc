# AGENT.md

本仓库是 **Anthropic 官方英文文档的只读本地/Git 镜像**（由 `scripts/sync_docs.py` 与 GitHub Actions 自动同步维护），用于 AI Agent 高精度本地检索。

> 约定：所有 `https_*_docs/` 正文目录及 `_meta/` 下文件均为自动生成，**请勿手动修改镜像文档内容**。

---

## 1. 三站目录与索引映射

| 官方站点 | 本地文档目录（纯 `.md`） | 根目录本地路径索引（优先读） | 元数据目录 | 涵盖内容 |
| :--- | :--- | :--- | :--- | :--- |
| `https://claude.com/docs` | `https_claude.com_docs/` | `https_claude.com_docs_llms.local.md` | `_meta/https_claude.com_docs/` | Claude.ai、Cowork、Connectors、MCP Apps、Plugins、Desktop 3P、Claude Tag、Government、Claude Science |
| `https://code.claude.com/docs` | `https_code.claude.com_docs/` | `https_code.claude.com_docs_llms.local.md` | `_meta/https_code.claude.com_docs/` | Claude Code CLI、IDE、Hooks、MCP、Subagents、Plugins、Agent SDK、企业管理 |
| `https://platform.claude.com` | `https_platform.claude.com_docs/` | `https_platform.claude.com_docs_llms.local.md` | `_meta/https_platform.claude.com_docs/` | Messages API、API Reference、Managed Agents、Tool Use、Models & Pricing、Client SDKs |

---

## 2. 推荐检索流程

1. **先读本地路径索引定位文件**
   根据问题所属产品，直接读取对应的 `*_llms.local.md`（例如 `https_code.claude.com_docs_llms.local.md`）。其中的链接已统一替换为**相对于仓库根目录的路径**（如 `https_code.claude.com_docs/hooks.md`），可直接打开目标 `.md` 阅读。
2. **跨站或关键词检索使用 `glob` / `rg`**
   三个 `https_*_docs/` 目录保留了官网多级子目录结构且不含索引噪声，适合直接用文件名匹配（`glob`）或全文检索（`rg`）定位细节。
3. **核对同步状态与时效性**
   - `_meta/<site_dir>/manifest.json`：记录最近同步时间（`updated_at`）、各文档 `lastmod`、`sha256` 与 `failed_pages`。
   - `_meta/<site_dir>/reconcile_report.json`：记录官网 `llms.txt` 与 `sitemap.xml` 的交叉核对差异。
   - `_meta/<site_dir>/llms.txt` & `sitemap.xml`：官网原始索引备份。
   - 若涉及极近期的版本变更且本地文档未体现，请提示用户或联网检索官网最新页面。

---

## 3. 自动化维护（仅改脚本时参考）

- **同步脚本**：`scripts/sync_docs.py`（支持 `--full`、`--site`、`--limit`、`--dry-run`）。
- **GitHub Actions**：`.github/workflows/sync-docs.yml`（每月 15 日北京时间 08:00 自动执行全量同步，亦支持 `workflow_dispatch` 手动触发）。
