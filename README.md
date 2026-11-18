# claude-doc

**简体中文** | [English](README_EN.md)

面向 AI Agent 与本地离线检索优化的 **Anthropic 全量英文官方文档只读镜像仓库**，通过单脚本（`scripts/sync_docs.py`）与 GitHub Actions 实现自动化同步、双源交叉核对与全量校验。

---

## 核心定位与设计原则

- **全量英文官方源**：完整镜像 Anthropic 目前拆分的三大官方文档站点（`claude.com/docs`、`code.claude.com/docs`、`platform.claude.com`）的英文 Markdown 原文（`*.md`）。
- **保留原始多级目录**：严格还原官网 URL 层级（例如 `https_platform.claude.com_docs/api/...`），避免单目录文件爆炸导致列目录截断，同时路径本身即语义，便于 AI Agent 使用 `glob` 与 `rg` 精准检索。
- **零 LLM 索引开销**：直接使用官网原版 `llms.txt` 与纯字符串替换生成的根目录 `*_llms.local.md`，零 Token 消耗、零幻觉风险。
- **仅保留英文页面**：跳过非英文多语言翻译页（部分站点的非英文译文仅涵盖约 342 篇且存在滞后），保证知识库最全且检索无重复噪声。
- **单源模型统一**：仅以三站官网的 `llms.txt` 与 `sitemap.xml` 作为数据源，并做双向交叉核对。

---

## 三站镜像与本地目录映射

| 官方站点 | 本地正文目录（纯 `.md`） | 根目录本地路径索引 | 元数据目录 | 示例基准篇数 (`llms` / `sitemap`) | 涵盖内容 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| [https://claude.com/docs](https://claude.com/docs) | [`https_claude.com_docs/`](https_claude.com_docs/) | [`https_claude.com_docs_llms.local.md`](https_claude.com_docs_llms.local.md) | [`_meta/https_claude.com_docs/`](_meta/https_claude.com_docs/) | 291 / 291 | Claude.ai、Cowork、Connectors、MCP Apps、Plugins、Desktop 3P、Claude Tag、Government、Claude Science |
| [https://code.claude.com/docs](https://code.claude.com/docs) | [`https_code.claude.com_docs/`](https_code.claude.com_docs/) | [`https_code.claude.com_docs_llms.local.md`](https_code.claude.com_docs_llms.local.md) | [`_meta/https_code.claude.com_docs/`](_meta/https_code.claude.com_docs/) | 205 / 204 | Claude Code CLI、IDE、Hooks、MCP、Subagents、Plugins、Agent SDK、企业管理（含 `claude-tag.md`） |
| [https://platform.claude.com](https://platform.claude.com) | [`https_platform.claude.com_docs/`](https_platform.claude.com_docs/) | [`https_platform.claude.com_docs_llms.local.md`](https_platform.claude.com_docs_llms.local.md) | [`_meta/https_platform.claude.com_docs/`](_meta/https_platform.claude.com_docs/) | 923 / 923 | Messages API、API Reference、Managed Agents、Tool Use、Models & Pricing、Client SDKs |

> 说明：基准篇数为建库调研时实测数据，实际篇数随 Anthropic 官网更新动态变化，可在各站点 `_meta/*/reconcile_report.json` 中查看最新核对明细。

---

## 仓库目录结构

```text
claude-doc/
├── .github/
│   └── workflows/
│       └── sync-docs.yml                       # GitHub Actions 定时与手动同步工作流
├── _meta/                                      # 元数据、原始索引备份与核对状态（脚本自动维护）
│   ├── https_claude.com_docs/
│   │   ├── llms.txt                            # 线上原始 llms.txt 备份
│   │   ├── sitemap.xml                         # 线上原始 sitemap.xml 备份
│   │   ├── reconcile_report.json               # llms.txt vs sitemap.xml 交叉核对报告
│   │   └── manifest.json                       # 各文档 URL / lastmod / sha256 / 同步状态
│   ├── https_code.claude.com_docs/
│   │   └── ...
│   └── https_platform.claude.com_docs/
│       └── ...
├── https_claude.com_docs/                      # claude.com/docs 英文原文镜像（纯 .md 目录树）
├── https_code.claude.com_docs/                 # code.claude.com/docs/en 英文原文镜像（纯 .md 目录树）
├── https_platform.claude.com_docs/             # platform.claude.com/docs/en 英文原文镜像（纯 .md 目录树）
├── https_claude.com_docs_llms.local.md         # claude.com/docs 本地路径索引（仓库根相对路径）
├── https_code.claude.com_docs_llms.local.md    # code.claude.com/docs 本地路径索引（仓库根相对路径）
├── https_platform.claude.com_docs_llms.local.md # platform.claude.com 本地路径索引（仓库根相对路径）
├── scripts/
│   ├── sync_docs.py                            # 四阶段统一同步脚本
│   └── requirements.txt                        # Python 依赖清单
├── .gitignore
├── AGENT.md                                    # AI Agent 检索操作指引
├── LICENSE                                     # MIT（附文档内容版权边界说明）
├── README.md                                   # 中文说明文档
└── README_EN.md                                # 英文说明文档
```

---

## 获取仓库

### 方式一：使用 Git Clone（推荐，方便后续同步更新）

```bash
# 完整克隆（保留全部提交历史）
git clone https://github.com/emplanetes/claude-doc.git

# 浅克隆（仅拉取最新文档快照，速度更快、占用更小）
git clone --depth 1 https://github.com/emplanetes/claude-doc.git
```

之后每月仓库自动同步后，只需在本地目录拉取最新变更即可：

```bash
cd claude-doc
git pull
```

### 方式二：直接下载 ZIP 压缩包（无需安装 Git）

1. 打开仓库主页：[https://github.com/emplanetes/claude-doc](https://github.com/emplanetes/claude-doc)
2. 点击页面右上角绿色 **`<> Code`** 按钮 -> **`Download ZIP`**（或直接点击下载：[claude-doc-main.zip](https://github.com/emplanetes/claude-doc/archive/refs/heads/main.zip)）
3. 解压到本地目录后，即可直接配合本地阅读器或 AI Agent 检索使用。

---

## AI Agent 使用指引

将本仓库克隆到本地或挂载到 Agent 工作区后，推荐按以下顺序检索（详见 [AGENT.md](AGENT.md)）：

1. **先读根目录 `*_llms.local.md` 定位文档**
   每个站点在根目录都有对应的 `*_llms.local.md`，其中所有文档 URL 已通过字符串规则替换为**相对于仓库根目录的路径**（例如 `https_platform.claude.com_docs/agents-and-tools/tool-use/bash-tool.md`），Agent 可直接读取目标文件。
2. **用 `glob` / `rg` 跨站检索正文**
   三个 `https_*_docs/` 正文目录内仅保留 `.md` 文档文件、无索引噪声，适合直接做全文关键词搜索。
3. **核对同步时效性**
   查看 `_meta/<site_dir>/manifest.json`（含 `updated_at`、`lastmod`、`sha256`、`failed_pages`）和 `reconcile_report.json` 即可确认最近一次同步状态。

---

## 本地阅读建议

如果你希望直接在本地以网页排版形式浏览这些 `.md` 文档，推荐使用 **Chromium 内核浏览器（Chrome / Edge 等）** 搭配 **[Markdown Reader](https://md-reader.github.io/)** 插件打开（从根目录的 `*_llms.local.md` 打开即可顺着链接点击跳转，体验接近离线文档站）：

- 官网主页：https://md-reader.github.io/
- Chrome 应用商店：[Markdown Reader - Chrome Web Store](https://chromewebstore.google.com/detail/markdown-reader/medapdbncneneejhbgcjceippjlfkmkg)
- Edge 加载项商店：[Markdown Reader - Microsoft Edge Addons](https://microsoftedge.microsoft.com/addons/detail/markdown-reader/djnplooklihmkcioemdjfcednfkpiodc)

> 提示：安装扩展后，请在浏览器的「扩展程序管理」中开启 **“允许访问文件 URL”**，即可直接渲染并跳转本地 `file://` 路径下的 Markdown 文件。

---

## 同步流水线原理（`scripts/sync_docs.py`）

脚本采用 **「1 个通用引擎 + 3 条站点配置」** 的设计，按四个阶段顺序执行：

1. **阶段一：元数据拉取（Metadata Fetch）**
   下载三站的 `llms.txt` 与 `sitemap.xml` 至 `_meta/<site_dir>/`，使用防 XXE 参数安全解析 XML 并提取 `<loc>` 与 `<lastmod>`。
2. **阶段二：双源交叉核对（Reconcile）**
   - 自动过滤非英文路由（如 `/docs/zh-CN/`）、`/_llms/*.txt` 语言索引、控制台 Web 路由及非文档资源；
   - 对路径与默认页（如 `index`、`.../index.md`）做统一归一化比对；
   - 输出 `reconcile_report.json`，记录 `only_in_llms`（如 `claude-tag`）与 `only_in_sitemap`，合并生成完整待同步清单。
3. **阶段三：抓取校验与安全落盘（Sync & Cleanup）**
   - **增量与全量模式**：默认模式下若本地文件存在且 `sitemap.xml` 的 `<lastmod>` 与 `manifest.json` 一致，则直接跳过请求（注：`platform.claude.com` 的 `sitemap.xml` 不提供 `<lastmod>`，每次会按 SHA-256 校验判重）；传 `--full` 时忽略 `lastmod`，对全部页面做 SHA-256 内容比对。
   - **限速与容错**：支持 `--workers` 与 `--delay` 请求间隔控制；遇到 `HTTP 429` 按 `Retry-After` 等待，遇到网络/TLS 瞬时异常自动指数退避重试；单页失败记入 `failed_pages` 并保留旧文件，不中断整体同步。
   - **内容合法性拦截**：校验 HTTP 200、响应非空且不以 `<!DOCTYPE` / `<html` 开头，防止把 404/拦截页面误存为 `.md`。
   - **精准清理**：仅在全量清单同步（未传 `--limit`）时，依据上一版 `manifest.json` 删除官网已下线的旧 `.md` 文件并清理空目录，绝不触碰非 `manifest` 登记的文件。
4. **阶段四：生成索引与汇总（Index & Summary）**
   在仓库根目录生成 `*_llms.local.md`，更新 `_meta/<site_dir>/manifest.json`，打印汇总表并在 GitHub Actions 中自动写入 `$GITHUB_STEP_SUMMARY`。

---

## 本地运行指南

### 环境要求

- Python 3.11+（已在 Python 3.13 验证通过）
- 安装依赖：

```bash
pip install -r scripts/requirements.txt
```

### 常用命令

```bash
# 1. 仅拉取元数据并做双源核对（不下载正文 .md）
python scripts/sync_docs.py --dry-run

# 2. 全量同步三站全部文档（强制核验所有页面 SHA-256）
python scripts/sync_docs.py --full --workers 2

# 3. 增量同步（有 lastmod 的站点跳过未变更页面）
python scripts/sync_docs.py --workers 2

# 4. 仅同步指定站点（可选：claude.com_docs / code.claude.com_docs / platform.claude.com）
python scripts/sync_docs.py --site code.claude.com_docs --full

# 5. 小批量测试（每站仅同步前 15 篇，不触发旧文件清理）
python scripts/sync_docs.py --limit 15
```

### 全部 CLI 参数说明

| 参数 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `--site` | 指定目标站点，可重复传入（`all`、`claude.com_docs`、`code.claude.com_docs`、`platform.claude.com`） | `all` |
| `--full` | 忽略 `lastmod` 缓存，对全部页面拉取并做 SHA-256 哈希比对 | 关闭 |
| `--limit N` | 每站最多同步 `N` 篇（`0` 表示不限制；`> 0` 时不执行过期文件清理） | `0` |
| `--dry-run` | 仅执行阶段一与阶段二（拉取元数据并生成 `reconcile_report.json`） | 关闭 |
| `--workers N` | 每站并发下载工作线程数 | `1` |
| `--delay S` | 两次 HTTP 请求之间的最小间隔秒数 | `0.3` |
| `--summary-file PATH` | 将 Markdown 同步摘要额外写入指定文件 | 无 |
| `--metrics-file PATH` | 将聚合统计数据（`added`/`updated`/`deleted`/`unchanged`/`failed`）写入 JSON 文件 | 无 |
| `--verbose` | 输出详细 Debug 日志 | 关闭 |

---

## GitHub Actions 自动化

工作流定义于 [`.github/workflows/sync-docs.yml`](.github/workflows/sync-docs.yml)：

- **定时触发**：每月 **15 日北京时间 08:00**（`cron: '0 0 15 * *'`，对应 UTC `00:00`）自动执行全量校验同步（`--full --workers 2`）。
- **手动触发（`workflow_dispatch`）**：可在 GitHub Actions 页面随时手动运行，支持两个参数：
  - `full_sync`：是否忽略 `lastmod` 缓存执行全量校验（默认 `true`）
  - `site`：选择同步 `all` 或单个站点（默认 `all`）
- **并发与权限**：声明 `permissions: contents: write` 以支持自动推送，通过 `concurrency` 防止定时与手动任务同时运行冲突。
- **分批 Commit 策略**（区分手动与自动触发，文档无变化时不产生正文 commit）：
  1. **正文与本地路径索引**（`https_*` 与 `*_llms.local.md`，有变化才提交）：
     - 手动：`文档手动更新：新增X 修改Y 删除Z 不变W`
     - 自动：`文档常规更新：新增X 修改Y 删除Z 不变W`
  2. **元数据与核对报告**（`_meta/`）：
     - 手动：`元数据手动更新（文档有变化）` / `元数据手动更新（无文档变更）`
     - 自动：`元数据常规检查（文档有变化）` / `元数据常规检查（无文档变更）`

---

## 版权与免责声明

- 本仓库中的同步脚本、工作流配置及辅助文件遵循 [MIT License](LICENSE)（Copyright (c) 2026 Roy Woo）。
- 仓库内镜像的所有官方文档内容版权均归 **Anthropic** 所有，并受 Anthropic 服务条款与相关协议约束。
- 本仓库仅用于技术学习、文档归档与 AI Agent 本地检索辅助；如涉及最新线上变更或权威条款，请以 Anthropic 官方网站为准。
