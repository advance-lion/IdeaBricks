# CLI Researcher CCCC Actor Capsule

This capsule packages the existing stage-1 CLI research agent for use in a
CCCC multi-agent workflow.

The actual working implementation lives at:

```text
../cli-catalog/
```

This capsule does not replace that implementation. It adds the CCCC-facing
contract around it: actor role, task template, artifact expectations,
acceptance criteria, and handoff rules.

## Purpose

The `cli-researcher` actor owns stage 1 of the workflow:

1. Research available CLI tools in the defined market scope.
2. Classify the tools using the team's existing CLI item structure.
3. Produce human-readable and machine-readable artifacts.
4. Hand off the catalog to the stage-2 ideation agent.

## Recommended CCCC Mapping

| Workflow concept | CCCC concept |
| --- | --- |
| Global leader | foreman / lead actor |
| Stage-1 agent | `cli-researcher` actor |
| Stage-1 assignment | `cccc_task` or `cccc_tracked_send` |
| Work state | `cccc_agent_state` |
| Research output | artifacts |
| Stage transition | handoff to ideation actor |

## Files

| File | Purpose |
| --- | --- |
| `capsule.manifest.json` | Machine-readable description of this CCCC actor capsule. |
| `CCCC_INTEGRATION.md` | CCCC-specific setup, task, state, and handoff instructions. |
| `actor-profile.json` | Machine-readable actor profile for the leader/foreman. |
| `actor.md` | Role, scope, operating rules, and non-goals for the actor. |
| `implementation-binding.md` | Binds this capsule to the actual working `cli-catalog` project. |
| `leader-runbook.md` | How the leader should assign, monitor, review, and hand off stage 1. |
| `task-template.md` | Template the leader can use when assigning stage-1 work. |
| `cccc-task-create.payload.json` | Ready-to-copy `cccc_task(action="create")` payload. |
| `agent-state-template.json` | Suggested compact `cccc_agent_state` update shape. |
| `stage2-handoff.payload.json` | Machine-readable handoff payload for the ideation actor. |
| `artifact-contract.md` | Required output files and naming contract. |
| `schema-binding.md` | How this capsule binds to the team's existing CLI item schema. |
| `acceptance-checklist.md` | Done criteria for leader review. |
| `handoff-to-ideator.md` | Instructions for the stage-2 idea-generation agent. |
| `examples/input.sample.json` | Example task input. |
| `examples/handoff-summary.sample.md` | Example concise handoff note. |

## Actual Worker Outputs

The existing worker writes outputs under:

```text
../cli-catalog/catalog/
```

Required outputs:

```text
catalog/
├── data/*.json
├── cli-catalog.md
└── cli-summary.json
```

## Integration Notes

Use `catalog/cli-summary.json` as the lightweight index for downstream agents.
Use `catalog/data/*.json` as the canonical full data.
Use `catalog/cli-catalog.md` for human review.

The stage-2 ideation agent should consume the existing worker outputs through
the schema in `../cli-catalog/schema/cli.schema.json`,
not through assumptions embedded in this capsule.
