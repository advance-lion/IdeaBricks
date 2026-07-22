# Artifact Contract

This contract defines the stage-1 files expected by the leader and downstream
agents.

## Actual Worker Output Directory

```text
../cli-catalog/catalog/
```

## Required Artifacts

| Artifact | Consumer | Purpose |
| --- | --- | --- |
| `catalog/data/*.json` | downstream agents | Canonical full CLI records, one file per CLI. |
| `catalog/cli-summary.json` | downstream agents | Lightweight routing index recommended for agent use. |
| `catalog/cli-catalog.md` | leader and humans | Human-readable Markdown catalog. |
| `meta/changelog.md` | leader and reviewers | Sync summary and recent changes. |
| `docs/FIELDS.md` | all agents | Field-level schema explanation. |
| `docs/SOURCES.md` | reviewers | Upstream source explanation. |

## Source of Truth

`catalog/data/*.json` is the canonical source of truth.

`catalog/cli-summary.json` is the recommended lightweight index for downstream
agents. It is optimized for scanning and routing, not for full detail.

`catalog/cli-catalog.md` is a review surface only. If the Markdown table and
JSON disagree, the leader should ask the `cli-researcher` actor to run
`python3 -m cli_catalog render` and validate again before stage 2 begins.

## Required Catalog Shape

The canonical item schema is:

```text
../cli-catalog/schema/cli.schema.json
```

Field documentation is in:

```text
../cli-catalog/docs/FIELDS.md
```

Do not introduce a new top-level `cli-catalog.json` contract unless the team
adds an explicit adapter.
