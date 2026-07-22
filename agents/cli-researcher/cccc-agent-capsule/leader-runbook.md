# Leader Runbook

This runbook describes how a CCCC leader or foreman should use the
`cli-researcher` capsule.

## 1. Confirm Schema Binding

Before assigning the task, confirm the existing implementation:

```text
../cli-catalog/
```

The authoritative schema is:

```text
../cli-catalog/schema/cli.schema.json
```

Do not ask the `cli-researcher` actor to redesign item fields unless the team
explicitly changes the existing `cli-catalog` project contract.

## 2. Create The Stage-1 Task

Use `task-template.md` as the task body.

Suggested CCCC task fields:

```json
{
  "action": "create",
  "title": "Stage 1: CLI market research catalog",
  "assignee": "cli-researcher",
  "type": "standard",
  "priority": "high",
  "notes": "Use cccc-agent-capsule/task-template.md. Run ../cli-catalog as the actual implementation. Preserve schema/cli.schema.json.",
  "checklist": [
    {
      "text": "Confirm cli-catalog implementation path"
    },
    {
      "text": "Run sync or render as needed"
    },
    {
      "text": "Validate with python3 -m cli_catalog validate"
    },
    {
      "text": "Confirm catalog/data/*.json and cli-summary.json exist"
    },
    {
      "text": "Review meta/changelog.md and hand off to ideation actor"
    }
  ]
}
```

## 3. Monitor Progress

The actor should keep its CCCC state focused on:

- Current command or research slice.
- Number of candidate tools found.
- Source quality issues.
- Blockers.
- Next action.

Avoid turning every local note into shared state. Durable facts belong in the
artifacts.

## 4. Review Outputs

Use `acceptance-checklist.md` before moving the task to `done`.

The most important checks are:

- `python3 -m cli_catalog validate` passes.
- `catalog/data/*.json` follows `schema/cli.schema.json`.
- `catalog/cli-summary.json` is suitable for machine consumption by stage 2.
- `catalog/cli-catalog.md` is consistent with the JSON.
- The actor did not generate or score product ideas.
- The handoff tells the ideation actor how to use the catalog.

## 5. Start Stage 2

After acceptance, create the ideation task with:

```json
{
  "summary_index": "../cli-catalog/catalog/cli-summary.json",
  "full_records": "../cli-catalog/catalog/data/*.json",
  "human_catalog": "../cli-catalog/catalog/cli-catalog.md",
  "schema": "../cli-catalog/schema/cli.schema.json",
  "field_docs": "../cli-catalog/docs/FIELDS.md",
  "changelog": "../cli-catalog/meta/changelog.md"
}
```

The ideation actor should use `cli-summary.json` for scanning and `data/*.json`
for full evidence.
