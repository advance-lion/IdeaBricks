# Handoff To Ideation Actor

## Source Artifact

For broad scanning, use:

```text
../cli-catalog/catalog/cli-summary.json
```

For full detail, use:

```text
../cli-catalog/catalog/data/*.json
```

## Human Review Artifact

Use:

```text
../cli-catalog/catalog/cli-catalog.md
```

only for quick scanning and discussion.

## Schema

Each full CLI item follows:

```text
../cli-catalog/schema/cli.schema.json
```

Field meanings are documented in:

```text
../cli-catalog/docs/FIELDS.md
```

Do not assume fields that are not present in the catalog.

## How To Use The Catalog

The ideation actor should derive ideas from:

- Repeated capabilities across tools.
- Repeated gaps or limitations.
- Workflow patterns implied by CLI usage.
- Underserved target users.
- Tool combinations that users currently stitch together manually.
- Strong technical primitives that lack a clear product layer.

Use the actual field names from `schema/cli.schema.json` and `docs/FIELDS.md`
when referencing catalog evidence.

## Reliability Rules

- Treat sourced fields as stronger evidence than unsourced notes.
- Treat low-confidence fields as inspiration, not fact.
- Do not generate ideas from a single weak claim.
- Do not invent missing tool capabilities.
- Do not ignore caveats in `research-method.md` or `source-log.md`.

## Expected Stage-2 Input

The ideation actor should receive:

```json
{
  "summary_index": "../cli-catalog/catalog/cli-summary.json",
  "full_records": "../cli-catalog/catalog/data/*.json",
  "schema": "../cli-catalog/schema/cli.schema.json",
  "field_docs": "../cli-catalog/docs/FIELDS.md",
  "goal": "Generate technically feasible product ideas derived from the CLI catalog."
}
```
