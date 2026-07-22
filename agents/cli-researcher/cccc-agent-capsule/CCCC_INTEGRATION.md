# CCCC Integration

This document is the CCCC-facing integration contract for the stage-1
`cli-researcher` actor.

The package is ready to be added to a CCCC workflow as a child actor, provided
the CCCC leader/foreman creates an actor using the profile below and assigns the
tracked task payload included in this capsule.

## Actor

Actor name:

```text
cli-researcher
```

Actor role:

```text
peer
```

Working directory:

```text
stage1-cli-researcher/cli-catalog
```

Guidance files, in order:

```text
stage1-cli-researcher/cli-catalog/AGENTS.md
stage1-cli-researcher/cccc-agent-capsule/actor.md
```

Machine-readable profile:

```text
stage1-cli-researcher/cccc-agent-capsule/actor-profile.json
```

## Required Runtime Capabilities

- Read and write files inside `stage1-cli-researcher/cli-catalog`.
- Run local Python commands.
- Optional network access for `python3 -m cli_catalog sync`.
- Optional `GITHUB_TOKEN` or `GH_TOKEN` for full GitHub stars refresh.

If network access is unavailable, the actor can still validate, summarize,
search, and hand off the bundled catalog snapshot.

## CCCC Task Creation

Use this payload with `cccc_task(action="create", ...)`:

```text
stage1-cli-researcher/cccc-agent-capsule/cccc-task-create.payload.json
```

The leader can also paste the same content into a tracked send or task card.

## Actor Execution

From the working directory:

```bash
python3 -m cli_catalog sync
python3 -m cli_catalog validate
python3 -m cli_catalog stats
```

If the team only needs to regenerate outputs from the bundled JSON:

```bash
python3 -m cli_catalog render
python3 -m cli_catalog summary
python3 -m cli_catalog validate
```

## State Updates

The actor should keep CCCC shared state compact. Use:

```text
stage1-cli-researcher/cccc-agent-capsule/agent-state-template.json
```

as the shape for `cccc_agent_state(action="update", ...)`.

Do not mirror every local command into CCCC state. Durable evidence belongs in
the generated catalog files and task outcome.

## Done Criteria

The stage-1 task can move to `done` when:

- `python3 -m cli_catalog validate` passes.
- `cli-catalog/catalog/cli-summary.json` exists.
- `cli-catalog/catalog/data/*.json` exists.
- `cli-catalog/catalog/cli-catalog.md` exists.
- `cli-catalog/meta/changelog.md` exists.
- The stage-2 handoff payload is available.

## Handoff To Stage 2

Use:

```text
stage1-cli-researcher/cccc-agent-capsule/stage2-handoff.payload.json
```

as the CCCC handoff payload for the ideation actor.

The ideation actor should:

- Start from `cli-catalog/catalog/cli-summary.json`.
- Read full records from `cli-catalog/catalog/data/*.json` when needed.
- Use `cli-catalog/schema/cli.schema.json` and `cli-catalog/docs/FIELDS.md`
  to understand fields.
- Treat the CLI catalog as research input, not as final product ideas.

## Important Integration Note

CCCC is a collaboration/runtime framework, not a package manager. This capsule
does not assume a universal `install agent package` command. It provides the
actor profile, task payload, guidance, acceptance checklist, and handoff
payload that a CCCC leader can use to add the worker as a child actor.
