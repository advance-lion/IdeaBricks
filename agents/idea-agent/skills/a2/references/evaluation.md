# Evaluation Phase

Act as the Evaluator role. Use `evaluation-input.json` and this rubric as the authoritative scoring surface.

## Logical phase boundary

- The default workflow evaluates in the same model session that generated the Ideas. This is role separation, not independent-context isolation.
- Freeze `generation.json`; do not revise Ideas, chains, gaps, or wording during evaluation.
- Copy `generation_sha256` and `evaluation_input_sha256` unchanged from the evaluator input; validation and ranking use them to bind the scores to the frozen Generation artifact and complete scoring surface.
- Do not reread `request.json`, `generation.json`, the Catalog, contracts, ledger, memory, or another run directory.
- Ignore remembered weights, generator preferences, sender viewpoints, and predicted winners when assigning raw dimension scores.
- Do not reward an Idea because it appears first or because its wording sounds preferred.
- Score all supplied Ideas before drawing comparisons.

## Rubric

Score each dimension from 0 through 100.

### user_value

Measure whether the target user has a concrete, meaningful, recurring problem and whether the solution improves the workflow.

### feasibility

Measure coverage by the referenced CLI chain, input/output compatibility, agent friendliness, MVP scope, and declared capability gaps.

### generality

Measure whether the product can extend to more users, neighboring domains, or repeated workflows without losing its core value.

### innovation

Measure novelty in the capability combination and product interaction, not novelty of the individual CLI tools.

### visual_expression

Measure whether users can directly understand or demonstrate the product's input, transformation, and result.

## Scoring discipline

- Use the full scale and avoid clustering every Idea around the same score.
- Ground each reason in fields present in the evaluation input.
- Lower feasibility when chains are partial or gaps affect the MVP core.
- Return risks separately rather than hiding them in reasons.
- Do not calculate totals or select a winner.

## Output contract

Write `evaluation.json` with exactly this shape:

```json
{
  "run_id": "the supplied run_id",
  "generation_sha256": "the supplied lowercase SHA-256",
  "evaluation_input_sha256": "the supplied evaluator-payload SHA-256",
  "evaluations": [
    {
      "idea_id": "idea_001",
      "dimensions": {
        "user_value": {"score": 82, "reason": "Evidence-based reason"},
        "feasibility": {"score": 88, "reason": "Evidence-based reason"},
        "generality": {"score": 75, "reason": "Evidence-based reason"},
        "innovation": {"score": 68, "reason": "Evidence-based reason"},
        "visual_expression": {"score": 80, "reason": "Evidence-based reason"}
      },
      "risks": ["Concrete risk"]
    }
  ]
}
```

- Evaluate every supplied Idea exactly once.
- Use finite numeric scores from 0 through 100.
- Give every score a non-empty reason and every Idea a risks array.
- Include only `run_id`, `generation_sha256`, `evaluation_input_sha256`, and `evaluations` at the root.
- Never include weights, totals, ranks, recommendations, or generator commentary.
