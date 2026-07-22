# CLI Catalog

自动从多个精选上游仓库同步开源 CLI 工具，整理成结构化 JSON 数据、Markdown 目录，以及适合传给其他 Agent 使用的轻量索引。

## 快速开始

```bash
cd cli-catalog
python3 -m cli_catalog sync
```

即使上游 commit 没变化，也强制重新同步：

```bash
python3 -m cli_catalog sync --force
```

只同步指定来源：

```bash
python3 -m cli_catalog sync --sources toolleeo-csv modern-unix
```

从已有 JSON 重新生成 Markdown 目录和 Agent 汇总索引：

```bash
python3 -m cli_catalog render
```

只生成给 Agent 使用的轻量 JSON 索引：

```bash
python3 -m cli_catalog summary
```

刷新 GitHub stars。`sync` 默认会刷新 stars；如果要完整刷新，建议设置 token：

```bash
export GITHUB_TOKEN=ghp_xxx   # 也可以用 GH_TOKEN
python3 -m cli_catalog sync
python3 -m cli_catalog sync --skip-stars   # 跳过 stars 刷新
```

查看统计信息：

```bash
python3 -m cli_catalog stats
```

搜索本地 CLI catalog：

```bash
python3 -m cli_catalog search video --category "Media"
python3 -m cli_catalog search ripgrep --agent-only
```

`search` 使用和 `cli-summary.json` 相同的分类归并规则；如果原始分类不同，会显示成 `Media & Graphics (from Video)` 这类形式。

查看某个 CLI 的完整 JSON：

```bash
python3 -m cli_catalog show yt-dlp/yt-dlp
```

查看 catalog 质量报告：

```bash
python3 -m cli_catalog quality
```

应用本地人工补充描述、tags、分类或安装信息：

```bash
python3 -m cli_catalog curate --dry-run
python3 -m cli_catalog curate
```

校验 catalog 数据和 Agent 汇总索引：

```bash
python3 -m cli_catalog validate
```

运行测试：

```bash
python3 -m unittest discover -s tests
```

## 项目结构

```text
cli-catalog/
├── catalog/
│   ├── data/              # 每个 CLI 一个 JSON 文件，是 canonical 数据
│   ├── cli-catalog.md     # 渲染后的 Markdown 目录
│   └── cli-summary.json   # 给 Agent 使用的轻量 JSON 索引
├── config/
│   ├── sources.json       # 要跟踪的上游仓库
│   ├── category_groups.json
│   ├── summary_categories.json
│   └── curated_overrides.json
├── state/
│   └── sources.json       # 每个来源上次同步的 commit
├── meta/
│   └── changelog.md       # 每次同步的摘要
└── cli_catalog/           # Python 同步与渲染代码
```

## 单条 CLI 数据

每个 CLI 的完整数据都保存在 `catalog/data/*.json` 中，一个文件对应一个工具。

字段说明见 [docs/FIELDS.md](docs/FIELDS.md)。  
数据来源说明见 [docs/SOURCES.md](docs/SOURCES.md)。

示例：`catalog/data/BurntSushi__ripgrep.json`

```json
{
  "id": "BurntSushi/ripgrep",
  "name": "ripgrep",
  "description": "Fast regex search respecting gitignore",
  "repo_url": "https://github.com/BurntSushi/ripgrep",
  "category": "Files & Search",
  "tags": ["search", "modern-unix"],
  "agent": { "score": 3, "friendly": true, "signals": ["modern-unix"] },
  "sources": [{ "id": "toolleeo-csv", "repo": "toolleeo/awesome-cli-apps-in-a-csv", "commit": "..." }],
  "meta": { "first_seen_at": "2026-07-21", "updated_at": "2026-07-21", "status": "active" }
}
```

## Agent 汇总索引

`catalog/cli-summary.json` 是推荐传给其他 Agent 的文件。它不是完整数据库，而是一个按类别分组的路由索引，方便人和 Agent 快速扫描。

结构如下：

```json
{
  "categories": [
    {
      "name": "Search",
      "count": 1,
      "columns": ["id", "cli", "function", "score"],
      "rows": [
        ["BurntSushi/ripgrep", "ripgrep", "Recursively searches directories for a regex pattern.", 3]
      ]
    }
  ]
}
```

每个分类里的 `columns` 说明 `rows` 中每一列的含义：

```json
["id", "cli", "function", "score"]
```

如果 Agent 需要安装命令、repo 链接、来源、skill URL、完整 tags 等详细信息，再根据 `detail_template` 读取对应的 `catalog/data/*.json`。

例如：

```text
BurntSushi/ripgrep -> catalog/data/BurntSushi__ripgrep.json
```

summary 会用 `config/summary_categories.json` 做一层展示用的分类归并。例如 `Video`、`Music`、`Movies` 会归到 `Media & Graphics`；原始单条 JSON 不会被改写。

summary 和 search 还会对明显的资源清单仓库做展示降权，例如 `awesome-*` 或仓库名就是 `awesome` 的条目。原始 JSON 中的 `agent.score` 不会被改写，但在路由索引和搜索结果里会按较低分数展示，避免 Agent 优先选择不可直接执行的清单仓库。

## 上游来源

| ID | 仓库 | 作用 |
|----|------|------|
| toolleeo-csv | toolleeo/awesome-cli-apps-in-a-csv | 主数据源，覆盖面最广 |
| cli-anything | HKUDS/CLI-Anything | Agent-native harness 与 CLI-Hub registry |
| awesome-ai-cli | luoyuctl/awesome-ai-cli | Agent 友好 CLI 筛选 |
| composio-agent-clis | ComposioHQ/awesome-agent-clis | Agent CLI 与 SKILL 文档 |
| modern-unix | ibraheemdev/modern-unix | 高质量现代 Unix 工具锚点 |
| awesome-cli-apps | agarrharr/awesome-cli-apps | 广度补充来源 |

## 手动编辑保护

如果某条 CLI 做过人工修正，可以在它的 `meta` 里设置保护标记，避免下次同步覆盖：

- `"manual_edit": true`：不覆盖 `description`、`homepage`、`install`
- `"locked_category": true`：不覆盖自动分类

`python3 -m cli_catalog curate` 会读取 `config/curated_overrides.json`，把本地人工补充应用到 `catalog/data/*.json`，并自动设置必要的保护标记。适合补齐高价值 CLI 的空描述，或标记明显的资源清单仓库。

## 合并优先级

`config/sources.json` 中的 `priority` 用来决定字段冲突时谁更权威：数字越小，优先级越高。

低优先级来源不会覆盖高优先级来源已有的 `description`、`homepage`、`install` 和 `category`，但仍然可以补充缺失字段，并贡献 `tags`、`sources`、Agent 信号等信息。

## Cursor Agent 用法

告诉 Agent：**「sync cli catalog」**。它应该运行：

```bash
python3 -m cli_catalog sync
```

然后查看 `meta/changelog.md`，总结新增、更新和总数。
