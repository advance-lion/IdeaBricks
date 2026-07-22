# CLI Catalog 字段说明

本文档说明 `catalog/data/*.json` 中每条 CLI 记录的字段含义、数据来源与维护规则。

每个 CLI 对应一个 JSON 文件，命名规则为 `{owner}__{repo}.json`（例如 `BurntSushi/ripgrep` → `BurntSushi__ripgrep.json`）。

---

## 示例记录

```json
{
  "id": "7thSamurai/steganography",
  "name": "Image Steganography Tool",
  "aliases": [],
  "description": "Simple C++ Encryption and Steganography tool that uses Password-Protected-Encryption to secure a file's contents.",
  "repo_url": "https://github.com/7thSamurai/steganography",
  "homepage": "",
  "install": {},
  "category": "Security",
  "tags": ["security", "security-and-encryption"],
  "agent": {
    "score": 1,
    "friendly": false,
    "signals": [],
    "skill_url": null
  },
  "sources": [
    {
      "id": "toolleeo-csv",
      "repo": "toolleeo/awesome-cli-apps-in-a-csv",
      "commit": "226eefaa1bc32f1eea2a03c56a2a1f2615c48f5f",
      "upstream_category": "security"
    }
  ],
  "meta": {
    "first_seen_at": "2026-07-21",
    "updated_at": "2026-07-21",
    "status": "active"
  }
}
```

---

## 顶层标识

### `id`

| 属性 | 说明 |
|------|------|
| **含义** | 全局唯一标识，通常为 GitHub 的 `owner/repo` |
| **用途** | 去重、合并多源数据、生成文件名 |
| **稳定性** | 仓库不改名则不变 |

### `name`

| 属性 | 说明 |
|------|------|
| **含义** | 展示名称 / 工具名称 |
| **来源** | 上游 CSV 或 README 列表 |
| **注意** | 不一定是 shell 里的命令名；可执行命令可能与 `name` 不同 |

### `aliases`

| 属性 | 说明 |
|------|------|
| **含义** | 别名列表（如 `rg` ↔ `ripgrep`） |
| **用途** | 搜索、去重、Agent 识别同一工具 |
| **默认** | 空数组 `[]` 表示暂无别名 |

---

## 介绍与链接

### `description`

| 属性 | 说明 |
|------|------|
| **含义** | 一句话功能描述 |
| **来源** | 上游 CSV / README |
| **维护** | sync 时若上游更新且未设置 `meta.manual_edit`，会被覆盖 |

### `repo_url`

| 属性 | 说明 |
|------|------|
| **含义** | 主仓库地址（canonical） |
| **用途** | 去重主键、跳转源码与文档 |
| **格式** | 规范化为 `https://github.com/owner/repo` |

### `homepage`

| 属性 | 说明 |
|------|------|
| **含义** | 非 GitHub 的官网或文档站 |
| **来源** | 上游 CSV 的 `homepage` 字段 |
| **默认** | 空字符串表示无独立主页或与 `repo_url` 相同 |

### `install`

| 属性 | 说明 |
|------|------|
| **含义** | 安装方式，键为包管理器，值为安装命令 |
| **示例** | `{"brew": "brew install ripgrep", "cargo": "cargo install ripgrep"}` |
| **默认** | 空对象 `{}` 表示尚未填充，可后续由 sync 或人工补全 |

---

## 分类与标签

### `category`

| 属性 | 说明 |
|------|------|
| **含义** | 大类，用于 Markdown 分组与浏览 |
| **来源** | 由上游 category slug 映射到 `config/category_groups.json` 中的分组 |
| **示例** | 上游 `security` → `Security` |
| **保护** | 设置 `meta.locked_category: true` 后 sync 不会覆盖 |

### `tags`

| 属性 | 说明 |
|------|------|
| **含义** | 更细粒度的多标签，便于筛选与搜索 |
| **来源** | 上游 slug、category 人类可读名、Agent 信号等 |
| **示例** | `security`, `security-and-encryption`, `json`, `mcp` |
| **数量** | 通常保留最多约 5 个 |

---

## GitHub Stars

### `github_stars`

| 属性 | 说明 |
|------|------|
| **含义** | 该 CLI 对应 GitHub 仓库的 star 数（`stargazers_count`） |
| **来源** | 每次 `sync` 时通过 GitHub API 拉取 |
| **类型** | 整数；仓库不存在或拉取失败时为 `null` |
| **去重** | 同一 `owner/repo` 的多个 catalog 条目共享同一 star 数 |

### `meta.github_stars_updated_at`

| 属性 | 说明 |
|------|------|
| **含义** | 最近一次刷新 star 数的时间 |
| **行为** | 每次 sync 的 star 刷新阶段更新 |

**API 限流说明**：约 2300+ 独立仓库需要 GitHub API。未设置 token 时限额约 60 次/小时；建议设置环境变量：

```bash
export GITHUB_TOKEN=ghp_xxx
python3 -m cli_catalog sync
```

也可用 `GH_TOKEN`。若触发限流，已拉取的部分会更新，其余保留旧值。

---

## Agent 相关：`agent`

```json
"agent": {
  "score": 1,
  "friendly": false,
  "signals": [],
  "skill_url": null
}
```

### `agent.score`（1～3）

| 分值 | 含义 |
|:----:|------|
| **1** | 普通 CLI，主要来自主 catalog（如 toolleeo CSV） |
| **2** | 偏现代、脚本友好（如 modern-unix 锚点工具） |
| **3** | 出现在 agent 专项列表（awesome-ai-cli、composio-agent-clis 等） |

### `agent.friendly`

| 属性 | 说明 |
|------|------|
| **含义** | 是否推荐 Agent 作为工具调用 |
| **规则** | 通常 `score >= 3` 时为 `true` |

### `agent.signals`

| 属性 | 说明 |
|------|------|
| **含义** | 判定依据标签，说明为何给出该评分 |
| **常见值** | `curated-agent-list`, `modern-unix`, `awesome-ai-cli`, `composio-agent-clis` |

### `agent.skill_url`

| 属性 | 说明 |
|------|------|
| **含义** | 供 Agent 使用的 SKILL 文档链接 |
| **来源** | 如 Composio 仓库中各 CLI 目录下的 `SKILL.md` |
| **默认** | `null` 表示暂无 |

---

## 溯源：`sources`

每条 source 表示该 CLI 从哪个上游被发现或更新过。

```json
{
  "id": "toolleeo-csv",
  "repo": "toolleeo/awesome-cli-apps-in-a-csv",
  "commit": "226eefaa1bc32f1eea2a03c56a2a1f2615c48f5f",
  "upstream_category": "security"
}
```

| 子字段 | 说明 |
|--------|------|
| `id` | 配置中的 source ID（见 `config/sources.json`） |
| `repo` | 上游 GitHub 仓库 |
| `commit` | 同步时该上游的 commit SHA，用于追溯与增量更新 |
| `upstream_category` | 上游原始分类 slug（可选） |

同一 CLI 被多个上游收录时，`sources` 数组会包含多条记录。

---

## 元数据：`meta`

### `meta.first_seen_at`

| 属性 | 说明 |
|------|------|
| **含义** | 首次写入 catalog 的日期（ISO 8601 日期） |
| **行为** | 新建时写入，之后一般不变 |

### `meta.updated_at`

| 属性 | 说明 |
|------|------|
| **含义** | 最后一次被 sync 更新的日期 |
| **行为** | 每次合并或更新时刷新 |

### `meta.status`

| 属性 | 说明 |
|------|------|
| **含义** | 条目状态 |
| **常见值** | `active`（正常）、`deprecated`（已废弃） |

### 可选保护字段

| 字段 | 说明 |
|------|------|
| `meta.manual_edit` | 为 `true` 时，sync 不覆盖 `description`、`homepage`、`install` |
| `meta.locked_category` | 为 `true` 时，sync 不覆盖 `category` |

---

## 字段关系概览

```text
id / repo_url          → 唯一标识
name / aliases         → 怎么称呼
description            → 干什么
category / tags        → 怎么分类、怎么搜
agent.*                → Agent 是否好用、依据是什么
sources[]              → 谁收录的、当时上游版本
meta.*                 → 何时入库/更新、是否保护手工修改
install / homepage     → 怎么装、去哪看（可后续补全）
```

---

## 数据流

```text
上游仓库 (CSV / README)
        ↓
   sync 解析与合并
        ↓
catalog/data/*.json     ← 真源（canonical）
        ↓
   render 渲染
        ↓
catalog/cli-catalog.md  ← 只读视图（勿手改）
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `docs/SOURCES.md` | 上游数据来源与 sync 规则 |
| `schema/cli.schema.json` | JSON Schema 定义 |
| `config/sources.json` | 跟踪的上游仓库 |
| `config/category_groups.json` | 上游 slug → 大类的映射 |
| `state/sources.json` | 各上游上次同步的 commit |
