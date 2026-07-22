# Task Template: Stage 1 CLI Research

## Title

Research and classify CLI tools for downstream idea generation

## Assignee

`cli-researcher`

## Objective

Research available CLI tools in the requested market scope and produce a
structured catalog using the existing `cli-catalog` implementation.

## Inputs

```json
{
  "research_scope": "",
  "target_users": [],
  "category_boundaries": [],
  "max_tools": null,
  "minimum_tools": null,
  "output_language": "zh-CN",
  "implementation_path": "../cli-catalog",
  "existing_cli_item_schema_path": "../cli-catalog/schema/cli.schema.json",
  "notes": ""
}
```

## Required Deliverables

```text
../cli-catalog/catalog/
├── data/*.json
├── cli-catalog.md
└── cli-summary.json

../cli-catalog/meta/
└── changelog.md
```

## Done Criteria

- `python3 -m cli_catalog validate` passes.
- `catalog/data/*.json` exists and follows `schema/cli.schema.json`.
- `catalog/cli-summary.json` exists for downstream agent scanning.
- `catalog/cli-catalog.md` provides a readable table for leader review.
- `meta/changelog.md` summarizes the latest sync.
- The actor has not generated, scored, or selected product ideas.

## Suggested CCCC Task Notes

```md
Stage: 1
Actor: cli-researcher
Implementation: ../cli-catalog/
Output directory: ../cli-catalog/catalog/
Schema source: ../cli-catalog/schema/cli.schema.json
Downstream consumer: ideation actor
```
