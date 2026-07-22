# Implementation Binding

This capsule is bound to the existing working implementation at:

```text
../cli-catalog/
```

That project is the real stage-1 worker. This capsule only describes how CCCC
should assign, run, validate, and hand off that worker.

## Existing Implementation

The implementation already contains:

- `AGENTS.md`: runtime guidance for the working agent.
- `README.md`: command usage and project overview.
- `schema/cli.schema.json`: authoritative single-CLI item schema.
- `docs/FIELDS.md`: field-level documentation.
- `docs/SOURCES.md`: source documentation.
- `config/*.json`: upstream sources, category grouping, and curation rules.
- `cli_catalog/`: Python implementation.
- `tests/`: validation and behavior tests.
- `catalog/`: generated outputs.

## Commands

Run from:

```bash
cd ../cli-catalog
```

Sync or refresh the catalog:

```bash
python3 -m cli_catalog sync
```

Force refresh:

```bash
python3 -m cli_catalog sync --force
```

Regenerate Markdown and summary from existing JSON:

```bash
python3 -m cli_catalog render
```

Generate only the downstream agent summary:

```bash
python3 -m cli_catalog summary
```

Validate outputs:

```bash
python3 -m cli_catalog validate
```

Show stats:

```bash
python3 -m cli_catalog stats
```

Search the catalog:

```bash
python3 -m cli_catalog search <query> --agent-only
```

Show one full CLI record:

```bash
python3 -m cli_catalog show <id-or-name>
```

## Actual Output Contract

The working implementation already defines the real output structure:

```text
../cli-catalog/catalog/
├── data/*.json          # canonical full CLI records, one file per CLI
├── cli-catalog.md       # human-readable Markdown catalog
└── cli-summary.json     # lightweight index recommended for downstream agents
```

The single-CLI item schema is:

```text
../cli-catalog/schema/cli.schema.json
```

## CCCC Handoff Rule

For downstream idea generation:

1. Start from `catalog/cli-summary.json` for broad scanning.
2. Use `catalog/cli-catalog.md` for human review.
3. Read `catalog/data/*.json` or run `python3 -m cli_catalog show <id>` when
   the ideation actor needs full detail for a specific CLI.

Do not require a separate `cli-catalog.json` unless the team explicitly adds an
adapter that bundles all per-CLI JSON files into one file.

## Current Verified State

Observed on 2026-07-22:

- Total CLIs: 2400
- Agent-friendly: 136
- Categories: 82
- Last sync: 2026-07-21T13:03:12+08:00
- Validation: passed with 0 warnings
