# Screenshot-to-App Factory · Team Contract

`idea-foreman` is the only global coordinator. It owns the user conversation, preserves a single `run_id`, decides when a candidate idea becomes selected, and sends the final MVP contract to `mvp-worker`.

```text
Offline maintenance:
  cli-researcher -> validate / refresh persistent CLI catalog snapshot

Online incubation:
  User brief -> Foreman
  -> Foreman reads the saved CLI catalog snapshot
  -> idea-agent (brief + snapshot; A2: generate, evaluate, rank)
  -> Foreman (select one candidate and freeze MVP contract)
  -> mvp-worker (screenshot -> runnable frontend -> browser QA -> delivery)
```

The peers do not dispatch one another. `cli-researcher` is not invoked by a normal incubation run; it owns periodic catalog maintenance. `idea-agent` replies only to the Foreman, and the Foreman is the only actor allowed to hand off to `mvp-worker` in the full-platform flow. The standalone Worker upload desk remains a testing entrance and may directly trigger `mvp-worker`.

## Shared handoff directory

For every platform run, the Foreman creates `handoffs/<run_id>/` in this workspace. The required evidence is:

| Stage | Owner | Required handoff |
| --- | --- | --- |
| Capability snapshot reference | `idea-foreman` | `cli-capability-form.json` referencing the persistent catalog |
| Idea incubation | `idea-agent` | `idea-shortlist.json`, `mvp-contract.json` |
| MVP delivery | `mvp-worker` | `worker-delivery.json`, preview, browser report |

`mvp-contract.json` must contain the selected `idea_id`, target user, pain point, visual direction, core interaction, source screenshot (if applicable), acceptance criteria, and a `handoff` object from `idea-foreman` to `mvp-worker`.

For this demo, the strategic core is not a generic idea generator: Idea Agent should translate the user brief into a scenario that invokes the Worker’s screenshot-to-runnable-app delivery chain. The scenario may be retail, ordering, content, or another domain, but the selected MVP must retain the chain: authorized screenshot → visual/layout understanding → runnable frontend → browser QA → source and evidence delivery.

`cli-capability-form.json` must be an adapter around the Stage-1 catalog, not a copied prose list. It records the exact `cli-summary.json`, canonical `catalog/data/` root, schema path, validation result, and the selected capability records for the current request.

The canonical persistent input for Idea Agent is `agents/cli-researcher/cli-catalog/catalog/idea-capability-snapshot.json`. Foreman materializes a run-scoped reference from it without starting CLI Researcher. CLI Researcher is requested only when the snapshot is missing, invalid, explicitly refreshed by the user, or expired under an operator-defined freshness policy.

If an imported peer's desktop runtime is unavailable, an operator may use that peer's documented delivery adapter to produce the same run-scoped handoff with an explicit fallback disclosure. This does not authorize a Stage-3 launch: `mvp-worker` remains blocked until the Foreman records the authorized screenshot input in `mvp-contract.json`.

## Runtime policy for the current demo

Foreman is a deterministic orchestration controller and does not require a coding CLI. Idea Agent requests the workspace Codex CLI first; if it is absent or does not produce valid handoffs, it requests Claude Code, then uses its deterministic delivery adapter only as the final fallback. CLI Researcher runs only as a catalog-maintenance job.

MVP Worker is configured for DGX Spark's OpenAI-compatible local VLM/LLM (`local-openai`) as the primary execution engine. It uses Codex CLI and then Claude Code only when that local service is unavailable or returns invalid output. Every switch is recorded in `runs/<run_id>/run-execution.json` and the Worker pipeline log; a fallback must never be presented as DGX local inference.
