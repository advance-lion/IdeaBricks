# Generation Phase

Generate products for real users and real workflows. Do not optimize for a competition demo unless the user explicitly asks for that.

## Normalize the request

- Extract domain, users, quantity, platform, privacy, local/cloud preference, and scoring-weight preferences.
- Do not ask follow-up questions.
- Show the inferred interpretation in the final workflow response or generation-debug response.
- Use the weight mapping in `contracts.md`.
- Write the canonical `normalized_request` shape from `contracts.md`; put additional non-weight constraints in `constraints.requirements`.
- Copy `normalized_request` unchanged from `request.json` to `generation.json`.

## Select and read the Catalog

- Treat `cli-summary.json` as a routing index, not as the generation context.
- List category names through `select-catalog.ps1`; never print the full index or all 2,400 detail records into model context.
- Translate a non-English request into specific English retrieval terms before building the slice.
- Cover several capability roles in the terms: user input, transformation, storage, integration, and visible output.
- Use the generated `catalog-slice.json` for capability inference and validation.
- Use only records whose `meta.status` is `active`.
- Treat a real A1 slice record missing a string `id` or `description` as a selector/validation failure. Only the legacy sample may skip such a record with a warning.
- Treat `agent.score` as agent friendliness and a prioritization signal, not reliability or product value.
- Do not exclude a relevant score-1 CLI merely because it is less agent-friendly; mature transformation tools may still complete a chain.
- Do not install, execute, or claim to have tested a CLI.

## Infer temporary capability types

For each relevant CLI, infer:

- a concise capability statement
- `input_types`
- `output_types`

Base inference on `description`, `category`, and `tags`. Use `unknown` rather than inventing unsupported certainty. Do not write inferred fields back to the Catalog.

## Build capability chains

- Prefer 2–5 CLI steps.
- Connect an output to a compatible or reasonably transformable next input.
- Keep each step's real Catalog `tool_id`.
- Prefer chains that cover a complete user workflow.
- Mark an incomplete chain `partial`, add a warning, and list the missing capability.
- If a core MVP feature or promised visible output lacks CLI coverage, mark the chain `partial` and declare that gap.
- Avoid adding a tool merely to increase chain length.

## Generate Ideas

Ensure each Idea:

- names a specific target user
- describes a concrete recurring problem
- proposes a product rather than a raw automation snippet
- includes a short end-to-end user flow
- identifies a minimal useful MVP
- traces its core behavior to one or more capability chains
- lists uncovered capabilities honestly
- differs materially from other Ideas in user, problem, or solution

Generate the requested count whenever enough valid combinations exist. Keep fewer valid Ideas rather than padding with duplicates.

## Prohibited output

Do not score, rank, shortlist, recommend, predict a winner, express a sender viewpoint, calculate totals, or read the evaluation rubric.
