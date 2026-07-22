# Stage 1 CLI Researcher

This is the deliverable package for stage 1 of the CCCC workflow.

It contains the real working CLI catalog agent plus the CCCC-facing capsule
needed by the leader/foreman to add it as a child actor in the larger flow.

## What To Deliver

Deliver this whole folder:

```text
stage1-cli-researcher/
```

Do not deliver only `cli-catalog/` unless the receiving team already knows how
to wire it into CCCC.

## Package Layout

```text
stage1-cli-researcher/
├── cli-catalog/             # actual stage-1 worker implementation
├── cccc-agent-capsule/      # CCCC actor/task/handoff wrapper
├── README.md
├── DELIVERY.md
└── package.manifest.json
```

## Core Worker

The actual working implementation is:

```text
cli-catalog/
```

It can sync, render, summarize, search, and validate the CLI catalog.

Common commands:

```bash
cd cli-catalog
python3 -m cli_catalog sync
python3 -m cli_catalog validate
python3 -m cli_catalog summary
python3 -m cli_catalog stats
```

## CCCC Integration

The CCCC-facing package is:

```text
cccc-agent-capsule/
```

Start with:

```text
cccc-agent-capsule/CCCC_INTEGRATION.md
```

Use it to create a CCCC actor named:

```text
cli-researcher
```

Machine-readable actor profile:

```text
cccc-agent-capsule/actor-profile.json
```

Recommended actor guidance:

```text
cli-catalog/AGENTS.md
cccc-agent-capsule/actor.md
```

Recommended task template:

```text
cccc-agent-capsule/task-template.md
```

Ready-to-use CCCC task payload:

```text
cccc-agent-capsule/cccc-task-create.payload.json
```

Leader runbook:

```text
cccc-agent-capsule/leader-runbook.md
```

Stage-2 handoff payload:

```text
cccc-agent-capsule/stage2-handoff.payload.json
```

## Outputs For Downstream Agents

The next stage should consume:

```text
cli-catalog/catalog/cli-summary.json
cli-catalog/catalog/data/*.json
cli-catalog/schema/cli.schema.json
cli-catalog/docs/FIELDS.md
```

Use `cli-summary.json` for broad scanning. Use `catalog/data/*.json` when full
detail and evidence are needed.

## Not Included

`forge-cli-to-mvp/` is not included in this package. It is a demo/front-end
project, not the stage-1 CCCC child actor.
