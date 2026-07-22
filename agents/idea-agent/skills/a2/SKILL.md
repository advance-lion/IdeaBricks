---
name: a2
description: Generate, role-separately evaluate, and deterministically rank product ideas grounded in an A1 CLI catalog, producing traceable capability chains and structured JSON for downstream agents. Use when a user asks for product ideas, startup ideas, CLI capability combinations, domain-specific agent products, idea scoring, or an A2 generation, evaluation, or full workflow.
---

# A2 CLI-Grounded Idea Workflow

Default to the complete single-session workflow: generate, switch roles, evaluate, and rank. Use `phase=generate` only for generation debugging. Use `phase=evaluate run_id=<run_id>` only for evaluation recovery or debugging.

## Resolve paths

- Resolve the project root from these candidates in order: the current working directory, non-empty `A2_PROJECT_ROOT`, then `$env:USERPROFILE\Projects\a2-agent`.
- For each candidate, probe only these exact Catalog locations with `Test-Path`:
  1. `catalog/` when it contains `cli-summary.json` and `data/`.
  2. `catalog/catalog/` when it contains those entries.
  3. Legacy fallback `catalog/sample-catalog.json`.
- Select the first candidate with a valid Catalog and treat that candidate as the project root. Stop with the probed candidate paths if none is valid.
- Never recursively list `catalog/data`, run `rg --files` over the Catalog, or print the full file inventory into context.
- Store each run under `runs/<run_id>/`.
- Construct the run path only by joining the resolved project root, `runs`, and a validated `run_id`; verify its full path remains directly under `<project-root>\runs`.
- Resolve bundled resources relative to this `SKILL.md`:
  - `references/contracts.md`
  - `references/generation.md`
  - `references/evaluation.md`
  - `scripts/select-catalog.ps1`
  - `scripts/phase-switch.ps1`
  - `scripts/rank.ps1`
- Use Windows PowerShell 5.1 compatible commands.
- Read Markdown and JSON explicitly as UTF-8 (for example, `Get-Content -Raw -Encoding UTF8`) so Chinese text and punctuation are preserved.

## Route the task

### Generate artifacts

Run these steps for the default workflow and for explicit `phase=generate`.

1. Read `references/contracts.md` and `references/generation.md` completely.
2. Parse the user's natural-language request without asking follow-up questions.
3. Apply defaults: cross-domain exploration, 5 Ideas, and the documented default weights.
4. Generate `a2_yyyyMMdd_HHmmss_<six-hex>` from the current local time and a fresh random suffix unless one is explicitly supplied. Never reuse an existing run directory.
5. Create `runs/<run_id>/request.json` using the request contract.
6. Prepare the Catalog:
   - When an A1 Catalog root exists, list its routing categories with `select-catalog.ps1 -Mode ListCategories`.
   - Select 3-6 exact category names for a focused request or 5-8 for cross-domain exploration.
   - Infer 8-15 specific English retrieval terms covering inputs, transformations, storage, and outputs. Avoid generic terms such as `tool`, `system`, or `data`.
   - Write `catalog-query.json` using the contract, then build `catalog-slice.json` and `catalog-selection.json` with `select-catalog.ps1 -Mode BuildSlice`.
   - Use `catalog-slice.json` as `<catalog-path>`. Never read the full summary or all detail JSON into model context.
   - If only the legacy sample exists, use it directly as `<catalog-path>`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\select-catalog.ps1 `
  -Mode ListCategories `
  -CatalogRoot <a1-catalog-root>

powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\select-catalog.ps1 `
  -Mode BuildSlice `
  -CatalogRoot <a1-catalog-root> `
  -QueryPath <run-dir>\catalog-query.json `
  -OutputPath <run-dir>\catalog-slice.json `
  -MetadataPath <run-dir>\catalog-selection.json
```

7. Read only `<catalog-path>` and use active entries with non-empty `id` and `description`.
8. Infer temporary capabilities and input/output types without modifying A1 data or the slice.
9. Create traceable capability chains and product Ideas according to `generation.md`.
10. Write `runs/<run_id>/generation.json`.
11. Validate it, repairing only reported errors and retrying at most three times:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\phase-switch.ps1 `
  -Mode ValidateGeneration `
  -CatalogPath <catalog-path> `
  -RequestPath <run-dir>\request.json `
  -GenerationPath <run-dir>\generation.json
```

12. Build the evaluator's sanitized, weight-free input:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\phase-switch.ps1 `
  -Mode BuildEvaluationInput `
  -CatalogPath <catalog-path> `
  -RequestPath <run-dir>\request.json `
  -GenerationPath <run-dir>\generation.json `
  -OutputPath <run-dir>\evaluation-input.json
```

Do not score, rank, recommend, predict a winner, or express a sender viewpoint while generating.

### Finish explicit generation debugging

When the task contains `phase=generate`, stop after the generation artifacts. Report the normalized request, selection summary, Idea count, warnings, `run_id`, and artifact paths. Do not read `references/evaluation.md`.

### Evaluate and rank

For the default workflow, continue immediately in the same session. For `phase=evaluate run_id=<run_id>`, start here with the existing run.

1. Freeze `generation.json`; never revise it during evaluation. Validate that the evaluator input still matches it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\phase-switch.ps1 `
  -Mode ValidateEvaluationInput `
  -GenerationPath <run-dir>\generation.json `
  -EvaluationInputPath <run-dir>\evaluation-input.json
```

2. Read `references/evaluation.md` and `runs/<run_id>/evaluation-input.json` only after this validation succeeds.
3. Switch to the Evaluator role. Treat the evaluation input as the authoritative scoring surface. Do not revisit or use generator preferences, prior recommendations, or weights when assigning dimension scores.
4. Score every supplied Idea before comparing them and write `runs/<run_id>/evaluation.json`.
5. Validate it, repairing only reported errors and retrying at most three times:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\phase-switch.ps1 `
  -Mode ValidateEvaluation `
  -GenerationPath <run-dir>\generation.json `
  -EvaluationInputPath <run-dir>\evaluation-input.json `
  -EvaluationPath <run-dir>\evaluation.json
```

The validation script may read generation data deterministically; do not inspect that file during the Evaluator role.

6. Invoke deterministic ranking without calculating totals yourself:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-root>\scripts\rank.ps1 `
  -RequestPath <run-dir>\request.json `
  -GenerationPath <run-dir>\generation.json `
  -EvaluationInputPath <run-dir>\evaluation-input.json `
  -EvaluationPath <run-dir>\evaluation.json `
  -OutputPath <run-dir>\result.json
```

7. Read `result.json` and return the normalized request, complete ranking, unique Top 1, main reasons, risks, warnings, `run_id`, and result path.

Do not describe the Evaluator as an independent context. Do not alter dimension scores to fit weights. Do not calculate totals in model prose. Do not ask the user to create another session after a successful default workflow.

## Failure rules

- Stop if the Catalog is unreadable or has no active usable tools.
- Stop if A1 category listing, query validation, detail loading, or slice validation fails.
- Never invent a `tool_id`.
- Keep incomplete but useful chains only when marked `partial` with explicit gaps.
- Treat the initial model output plus three repairs as the maximum for each phase.
- Preserve the Catalog query and every artifact already written before a failure; retain command error output as the diagnostic when selection metadata was not produced.
- Never enter the Evaluator role after generation validation fails.
- Never continue to ranking after evaluation validation fails.
