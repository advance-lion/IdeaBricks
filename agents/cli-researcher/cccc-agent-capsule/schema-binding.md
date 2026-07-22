# Schema Binding

The team already has a designed structure for a single CLI item. This capsule
binds to that existing design instead of replacing it.

## Rule

The existing CLI item schema is authoritative:

```text
../cli-catalog/schema/cli.schema.json
```

Field documentation:

```text
../cli-catalog/docs/FIELDS.md
```

The `cli-researcher` actor may add CCCC-facing wrapper metadata only when it
does not break downstream consumers.

## What To Provide To The Leader

Before the leader assigns the task, confirm the implementation path:

```text
../cli-catalog/
```

The current project already provides the schema, field documentation, examples,
generated catalog data, and tests.

## What This Capsule Adds

This capsule adds:

- Output file names.
- Output directory convention.
- Done criteria.
- Handoff rules.
- Review expectations.

This capsule does not add:

- New required fields inside a CLI item.
- New category taxonomy unless requested.
- New scoring logic.
- Product idea generation.

## Compatibility Checklist

- The ideation actor can parse `catalog/cli-summary.json`.
- The ideation actor can fetch full records from `catalog/data/*.json`.
- The leader knows which schema version was used.
- The research actor has documented any fields it could not fill.
- The source log explains where factual claims came from.
- The handoff summary names the fields the ideation actor should pay attention
  to, using the team's actual field names.
