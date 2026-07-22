# CLI Catalog 数据来源说明

本文档说明 catalog 中每个 CLI 的数据来自哪些上游仓库，以及 sync 如何拉取、合并与去重。

> 配置真源：`config/sources.json`  
> 同步状态：`state/sources.json`  
> 每条 CLI 的溯源详情：JSON 中的 `sources[]` 字段

---

## 概览

当前 catalog 跟踪 **6 个 GitHub 上游仓库**，手动执行 `python3 -m cli_catalog sync` 时拉取更新。

| 统计项 | 数值 |
|--------|------|
| 去重后 CLI 总数 | **2400** |
| Agent-friendly（★★★） | **142** |
| 分类数 | **82** |
| 上次同步 | 2026-07-21 |

**说明**：下表「收录条数」是各源**独立解析出的链接数**，同一工具会出现在多个源中；合并后按 `repo_url` / 专用 `id` 去重。

---

## 上游来源一览

| ID | 仓库 | 角色 | 优先级 | 解析文件 | 收录条数* | 最后 commit |
|----|------|------|:------:|----------|----------:|-------------|
| `toolleeo-csv` | [toolleeo/awesome-cli-apps-in-a-csv](https://github.com/toolleeo/awesome-cli-apps-in-a-csv) | 主数据源 | 1 | `data/apps.csv`, `data/categories.csv` | 2068 | `226eefaa` |
| **`cli-anything`** | **[HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything)** | **Agent-native  harness** | **2** | **`registry.json`, `public_registry.json`** | **101** | **`bc536c9b`** |
| `awesome-ai-cli` | [luoyuctl/awesome-ai-cli](https://github.com/luoyuctl/awesome-ai-cli) | Agent 筛选 | 2 | `README.md` | 22 | `b1957619` |
| `composio-agent-clis` | [ComposioHQ/awesome-agent-clis](https://github.com/ComposioHQ/awesome-agent-clis) | Agent 筛选 | 2 | `README.md` | 18 | `9f765d2d` |
| `modern-unix` | [ibraheemdev/modern-unix](https://github.com/ibraheemdev/modern-unix) | 高质量锚点 | 3 | `README.md` | 28 | `67ee5aba` |
| `awesome-cli-apps` | [agarrharr/awesome-cli-apps](https://github.com/agarrharr/awesome-cli-apps) | 广度补充 | 3 | `readme.md` | 487 | `598390e9` |

\* 来自 `state/sources.json` 最近一次 sync 的 `entry_count`。

**Catalog 中至少被一个源收录的次数**（可重叠）：

| Source ID | 出现在 catalog 中的 CLI 数 |
|-----------|---------------------------:|
| toolleeo-csv | 2050 |
| awesome-cli-apps | 487 |
| cli-anything | 99 |
| modern-unix | 28 |
| awesome-ai-cli | 22 |
| composio-agent-clis | 18 |

---

## 各来源详细说明

### 1. toolleeo-csv（主数据源）

| 项目 | 内容 |
|------|------|
| **GitHub** | https://github.com/toolleeo/awesome-cli-apps-in-a-csv |
| **分支** | `master` |
| **角色** | `primary` — 广度底座，约 2200+ CLI |
| **解析方式** | CSV：`data/apps.csv` + `data/categories.csv` |
| **提供字段** | `name`, `description`, `repo_url`, `homepage`, 上游分类 slug |
| **分类逻辑** | 上游 slug → `config/category_groups.json` 映射为大类 |
| **特点** | 结构化 CSV，最适合程序解析；覆盖最全 |

**CSV 字段示例**（`apps.csv`）：

```text
category,name,homepage,git,description
security,steganography,,https://github.com/7thSamurai/steganography,...
```

---

### 2. cli-anything（Agent-native harness 核心来源）⭐

| 项目 | 内容 |
|------|------|
| **GitHub** | https://github.com/HKUDS/CLI-Anything |
| **CLI-Hub 网站** | https://clianything.cc/ |
| **分支** | `main` |
| **角色** | `agent-filter` — **专为 Agent 设计的 CLI harness 生态** |
| **解析方式** | 结构化 JSON：`registry.json`（79 条 monorepo harness）+ `public_registry.json`（22 条公共 CLI） |
| **提供字段** | `name`, `display_name`, `description`, `category`, `install_cmd`, `entry_point`, `skill_md`, `homepage` |
| **对 catalog 的影响** | `agent.score = 3`，`agent.friendly = true`，写入 `agent.skill_url`，`install.pip` 等 |
| **特点** | 45k+ stars；为 Blender/GIMP/Obsidian 等专业软件生成 Agent 可调用 CLI；每条带 SKILL.md |

**为什么重要（与 catalog 目标高度契合）**：

- 不是「普通 CLI 清单」，而是 **Agent-Native** 工具库
- 每条 harness 有 **JSON 输出、非交互、SKILL 文档**
- 通过 `cli-hub install <name>` 统一管理
- 与 Cursor / Claude Code / OpenClaw 等 Agent 工作流直接对齐

**ID 规则**：

- 有独立 `source_url` 时：用 GitHub `owner/repo`（如外部 Zotero CLI）
- 无独立仓库时：`HKUDS/CLI-Anything/{name}`（monorepo 子 harness）

**示例 JSON 文件**：`catalog/data/HKUDS__CLI-Anything__gimp.json`

---

### 3. awesome-ai-cli（Agent 友好筛选）

| 项目 | 内容 |
|------|------|
| **GitHub** | https://github.com/luoyuctl/awesome-ai-cli |
| **分支** | `main` |
| **角色** | `agent-filter` — 标注 AI Agent 时代适用的 CLI |
| **解析方式** | 解析 `README.md` 中的 GitHub 链接 |
| **对 catalog 的影响** | `agent.score = 3`，`agent.friendly = true`，分类倾向 `AI & Agents` |
| **特点** | 强调 JSON 输出、MCP、非交互、跨平台 Agent 可用性 |

---

### 4. composio-agent-clis（Agent CLI + SKILL）

| 项目 | 内容 |
|------|------|
| **GitHub** | https://github.com/ComposioHQ/awesome-agent-clis |
| **分支** | `master` |
| **角色** | `agent-filter` — 面向 Cursor / Claude Code 等 Agent 的 CLI 列表 |
| **解析方式** | 解析 `README.md` 中的链接与 `[skill](...)` |
| **对 catalog 的影响** | 提升 `agent.score`；写入 `agent.skill_url`（若有 SKILL.md） |
| **特点** | 每个 CLI 常配有 SKILL 文档，便于 Agent 学习安装与用法 |

---

### 5. modern-unix（高质量锚点）

| 项目 | 内容 |
|------|------|
| **GitHub** | https://github.com/ibraheemdev/modern-unix |
| **分支** | `master` |
| **角色** | `anchor` — 现代 Unix 工具替代品精选 |
| **解析方式** | 解析 `README.md` 中 `<code>tool</code>` 链接 |
| **对 catalog 的影响** | `agent.score ≥ 2`，信号 `modern-unix` |
| **典型工具** | ripgrep, bat, fd, fzf, zoxide, jq, httpie 等 |

---

### 6. awesome-cli-apps（广度补充）

| 项目 | 内容 |
|------|------|
| **GitHub** | https://github.com/agarrharr/awesome-cli-apps |
| **分支** | `master` |
| **角色** | `breadth` — 社区维护的大型 CLI 清单 |
| **解析方式** | 解析 `readme.md`（小写）中的 Markdown 链接 |
| **对 catalog 的影响** | 补漏、交叉验证；`category` 取 README 章节标题 |
| **特点** | ~19k stars，分类细；与 toolleeo 有大量重叠，合并后去重 |

---

## 数据流与合并规则

```text
┌─────────────────────────────────────────────────────────────┐
│  5 个 GitHub 上游仓库                                         │
└───────────────┬─────────────────────────────────────────────┘
                │  python3 -m cli_catalog sync
                ▼
┌─────────────────────────────────────────────────────────────┐
│  解析 → 统一 CliEntry → 按 repo_url 去重 → 合并 sources[]    │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  catalog/data/{owner}__{repo}.json   （canonical 真源）       │
└───────────────┬─────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────┐
│  catalog/cli-catalog.md              （Markdown 视图）        │
└─────────────────────────────────────────────────────────────┘
```

### 去重与合并（`config/sources.json` → `merge_rules`）

| 规则 | 说明 |
|------|------|
| **主键** | `repo_url`（GitHub `owner/repo`） |
| **备选键** | `normalized_name`（命令名归一化） |
| **别名** | `rg` → `ripgrep`，`exa` → `eza` |
| **字段优先级** | `priority` 数字越小越权威；低优先级来源不会覆盖高优先级已有的描述、主页、安装命令和分类 |
| **合并** | 同一工具多源出现时，`sources[]` 追加；`tags` 合并；`agent.score` 取最高值 |

### 单条 CLI 如何追溯来源

每个 JSON 的 `sources` 数组记录「从哪个上游被发现/更新过」：

```json
"sources": [
  {
    "id": "toolleeo-csv",
    "repo": "toolleeo/awesome-cli-apps-in-a-csv",
    "commit": "226eefaa1bc32f1eea2a03c56a2a1f2615c48f5f",
    "upstream_category": "security"
  },
  {
    "id": "modern-unix",
    "repo": "ibraheemdev/modern-unix",
    "commit": "67ee5aba0e5660b76cc1a437c64ad165212148d1"
  }
]
```

---

## 更新机制

| 项目 | 说明 |
|------|------|
| **触发方式** | 手动：`python3 -m cli_catalog sync` |
| **增量逻辑** | 对比 `state/sources.json` 中各源 commit；无变化则跳过该源 |
| **强制全量** | `python3 -m cli_catalog sync --force` |
| **指定源** | `python3 -m cli_catalog sync --sources toolleeo-csv modern-unix` |
| **变更摘要** | 写入 `meta/changelog.md` |

---

## 范围说明（收录什么 / 不收录什么）

### 收录范围

- 全球**开源** CLI / TUI 工具
- 以 GitHub 仓库链接为主（`repo_url` 可解析为 `owner/repo`）
- 偏 **Agent 可用** 的工具在 `awesome-ai-cli`、`composio-agent-clis` 中额外加权

### 当前未作为独立源跟踪

| 类型 | 说明 |
|------|------|
| Homebrew 全量 formulae | 体量过大，噪声高 |
| npm/cargo 全库搜索 | 未纳入，可作为未来扩展 |
| GitHub topic 爬虫 | 未纳入，可作为发现层扩展 |
| tldr-pages | 文档索引，非 discovery 列表 |

---

## 相关文件索引

| 文件 | 用途 |
|------|------|
| `config/sources.json` | 上游仓库列表与解析器配置 |
| `config/category_groups.json` | toolleeo 分类 slug → 大类映射 |
| `state/sources.json` | 各源上次 sync 的 commit 与统计 |
| `meta/changelog.md` | 每轮 sync 变更摘要 |
| `docs/FIELDS.md` | 单条 JSON 字段说明 |
| `catalog/data/*.json` | 每个 CLI 的 canonical 数据 |
| `catalog/cli-catalog.md` | 按分类渲染的 Markdown 总表 |

---

## 添加新上游源

1. 在 `config/sources.json` 的 `sources` 数组中新增一项（`id`, `repo`, `branch`, `files`, `parser`, `role`, `priority`）
2. 若需新解析器，在 `cli_catalog/parsers/` 中实现并在 `cli_catalog/sync.py` 注册
3. 执行 `python3 -m cli_catalog sync --sources <新源-id>`
4. 检查 `meta/changelog.md` 与 `state/sources.json` 是否更新正常
