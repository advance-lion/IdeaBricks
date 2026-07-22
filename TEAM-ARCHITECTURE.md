# Screenshot-to-App Factory · Team Contract

`idea-foreman` is the only global coordinator. It owns the user conversation, preserves a single `run_id`, decides when a candidate idea becomes selected, and sends the final MVP contract to `mvp-worker`.

```text
User brief
  -> Foreman
  -> market-scout (CLI capability form)
  -> idea-agent (A2: generate, evaluate, rank)
  -> Foreman (select one candidate and freeze MVP contract)
  -> mvp-worker (screenshot -> runnable frontend -> browser QA -> delivery)
```

The peers do not dispatch one another. `market-scout` and `idea-agent` reply only to the Foreman; the Foreman is the only actor allowed to hand off to `mvp-worker` in the full-platform flow. The standalone Worker upload desk remains a testing entrance and may directly trigger `mvp-worker`.

## Shared handoff directory

For every platform run, the Foreman creates `handoffs/<run_id>/` in this workspace. The required evidence is:

| Stage | Owner | Required handoff |
| --- | --- | --- |
| Capability discovery | `market-scout` | `cli-capability-form.json` |
| Idea incubation | `idea-agent` | `idea-shortlist.json`, `mvp-contract.json` |
| MVP delivery | `mvp-worker` | `worker-delivery.json`, preview, browser report |

`mvp-contract.json` must contain the selected `idea_id`, target user, pain point, visual direction, core interaction, source screenshot (if applicable), acceptance criteria, and a `handoff` object from `idea-foreman` to `mvp-worker`.
