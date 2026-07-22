# Delivery Notes

## Short Message For The Team

```md
I am delivering `stage1-cli-researcher/`.

It contains:

1. `cli-catalog/`: the actual stage-1 worker that syncs, classifies, validates,
   and outputs the CLI catalog.
2. `cccc-agent-capsule/`: the CCCC integration wrapper with actor guidance,
   task template, acceptance checklist, and handoff instructions.

CCCC should add this as actor `cli-researcher`.

The leader should use:
- `cccc-agent-capsule/CCCC_INTEGRATION.md`
- `cccc-agent-capsule/actor-profile.json`
- `cccc-agent-capsule/cccc-task-create.payload.json`
- `cccc-agent-capsule/actor.md`
- `cccc-agent-capsule/task-template.md`
- `cccc-agent-capsule/leader-runbook.md`
- `cccc-agent-capsule/stage2-handoff.payload.json`

The downstream ideation actor should consume:
- `cli-catalog/catalog/cli-summary.json`
- `cli-catalog/catalog/data/*.json`
- `cli-catalog/schema/cli.schema.json`
- `cli-catalog/docs/FIELDS.md`
```

## CCCC Actor Setup

Actor name:

```text
cli-researcher
```

Actor role:

```text
Stage-1 CLI research and catalog generation worker.
```

Guidance files:

```text
cli-catalog/AGENTS.md
cccc-agent-capsule/actor.md
```

Actor profile:

```text
cccc-agent-capsule/actor-profile.json
```

Task template:

```text
cccc-agent-capsule/task-template.md
```

CCCC task create payload:

```text
cccc-agent-capsule/cccc-task-create.payload.json
```

Acceptance checklist:

```text
cccc-agent-capsule/acceptance-checklist.md
```

Handoff document:

```text
cccc-agent-capsule/handoff-to-ideator.md
```

Machine-readable stage-2 handoff:

```text
cccc-agent-capsule/stage2-handoff.payload.json
```

## Commands The Actor Can Run

From `stage1-cli-researcher/cli-catalog/`:

```bash
python3 -m cli_catalog sync
python3 -m cli_catalog sync --force
python3 -m cli_catalog render
python3 -m cli_catalog summary
python3 -m cli_catalog validate
python3 -m cli_catalog stats
python3 -m cli_catalog search <query> --agent-only
python3 -m cli_catalog show <id-or-name>
```

## Done Criteria

Stage 1 is done when:

- `python3 -m cli_catalog validate` passes.
- `cli-catalog/catalog/cli-summary.json` exists.
- `cli-catalog/catalog/data/*.json` exists.
- `cli-catalog/catalog/cli-catalog.md` exists.
- `cli-catalog/meta/changelog.md` is available for sync summary.
- The ideation actor has been given the handoff paths.

## Important Boundary

This package is the stage-1 CCCC child actor deliverable.

`forge-cli-to-mvp/` is a demo UI and should not be treated as the stage-1 actor
unless the team explicitly adds a visualization/demo step to the workflow.
