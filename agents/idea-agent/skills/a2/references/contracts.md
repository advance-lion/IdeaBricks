# A2 JSON Contracts

Use these contracts exactly. Preserve stable IDs within one run.

## Request

`request.json`:

```json
{
  "run_id": "a2_20260721_120000_a1b2c3",
  "raw_request": "User text",
  "normalized_request": {
    "domain": "education",
    "target_users": ["teachers"],
    "idea_count": 5,
    "constraints": {
      "local_first": true,
      "privacy_sensitive": true,
      "target_platform": "unspecified",
      "requirements": []
    }
  },
  "weights": {
    "user_value": 0.25,
    "feasibility": 0.25,
    "generality": 0.20,
    "innovation": 0.20,
    "visual_expression": 0.10
  }
}
```

Defaults:

- Build `run_id` from the current local timestamp plus a fresh six-hex suffix; never reuse an existing run directory.
- Missing domain: `cross-domain`.
- Missing target users: `["general users"]`.
- Missing count: `5`.
- Missing local-first preference: `false`.
- Missing privacy sensitivity: `false`.
- Missing target platform: `unspecified`.
- Missing extra requirements: `[]`.
- Copy `normalized_request` unchanged into `generation.json`.
- Explicit percentages override defaults.
- “More important” multiplies that dimension's default weight by 1.5.
- “Most important” multiplies that dimension's default weight by 2.
- Leave raw weights unnormalized; `rank.ps1` normalizes them.

## Catalog query and slice

When the A1 routing index is available, write `catalog-query.json`:

```json
{
  "run_id": "a2_20260721_120000_a1b2c3",
  "categories": ["Productivity", "Text & Docs", "Data & JSON"],
  "keywords": ["teacher", "worksheet", "document", "ocr", "sqlite", "review queue", "dashboard", "pdf export"],
  "max_candidates": 60
}
```

Rules:

- Use only exact category names returned by `select-catalog.ps1 -Mode ListCategories`.
- Select 3-6 categories for a focused request or 5-8 for cross-domain exploration.
- Supply 8-15 specific English retrieval terms. Cover user inputs, transformations, storage, integrations, and visible outputs.
- Avoid generic terms such as `tool`, `system`, `application`, or `data`.
- Keep `max_candidates` at `60` unless debugging a boundary condition.

`select-catalog.ps1` writes:

- `catalog-slice.json`: an array of validated A1 detail records suitable for existing A2 validators.
- `catalog-selection.json`: source version, query, selected IDs, fallback count, and warnings.

The selector may fill an empty detail `description` from the summary `function` in the run-local slice. It must never modify A1 source files.

## Generation

`generation.json`:

```json
{
  "run_id": "a2_20260721_120000_a1b2c3",
  "normalized_request": {
    "domain": "education",
    "target_users": ["teachers"],
    "idea_count": 5,
    "constraints": {
      "local_first": true,
      "privacy_sensitive": true,
      "target_platform": "unspecified",
      "requirements": []
    }
  },
  "capability_chains": [
    {
      "chain_id": "chain_001",
      "domain": "education",
      "chain_summary": "Transform classroom images into editable notes",
      "status": "partial",
      "warnings": ["Editable document conversion is not covered"],
      "steps": [
        {
          "order": 1,
          "tool_id": "ImageMagick/ImageMagick",
          "capability": "Preprocess images",
          "input_types": ["image"],
          "output_types": ["normalized_image"]
        }
      ],
      "capability_gaps": ["Convert OCR output into an editable document"]
    }
  ],
  "ideas": [
    {
      "idea_id": "idea_001",
      "name": "Local Lesson Material Digitizer",
      "domain": "education",
      "target_user": "Teachers",
      "problem": "Printed classroom material is hard to reuse",
      "solution": "Convert local images into editable structured notes",
      "user_flow": ["Select files", "Process locally", "Review output"],
      "capability_chain_ids": ["chain_001"],
      "tool_ids": ["ImageMagick/ImageMagick"],
      "mvp_features": ["Local import", "Preview", "Export"],
      "capability_gaps": []
    }
  ],
  "warnings": []
}
```

Rules:

- Use unique `chain_id` and `idea_id` values.
- Reference only active Catalog IDs.
- Use 2–5 tools for a normal chain.
- A single-tool fallback must be `partial` and explain its gap.
- A `complete` chain must have no capability gaps; a `partial` chain must list at least one explicit capability gap.
- Use `unknown` when an inferred type cannot be established.
- Never include scores, totals, ranks, or recommendations.

## Evaluation input

`evaluation-input.json` contains only:

- `run_id`
- `generation_sha256`, the lowercase SHA-256 of the frozen `generation.json`
- `evaluation_input_sha256`, the lowercase SHA-256 of the canonical evaluator payload excluding this hash field
- sanitized `product_context` without raw user text or weights
- Ideas
- referenced capability chains
- minimal referenced CLI summaries
- the five-dimension rubric

It must not contain `raw_request`, `weights`, prompts, reasoning, self-evaluation, prior messages, or unrelated Catalog entries.

Validation and ranking must recompute both hashes and reject a mismatch. The Evaluator must copy `generation_sha256` and `evaluation_input_sha256` unchanged into `evaluation.json`; this prevents scores from being reused after either the frozen Generation artifact or the scoring surface changes.
