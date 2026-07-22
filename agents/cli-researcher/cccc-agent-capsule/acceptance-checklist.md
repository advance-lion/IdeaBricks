# Acceptance Checklist

Use this checklist before moving the stage-1 task to `done`.

## Required Files

- [ ] `../cli-catalog/catalog/data/*.json`
- [ ] `../cli-catalog/catalog/cli-summary.json`
- [ ] `../cli-catalog/catalog/cli-catalog.md`
- [ ] `../cli-catalog/meta/changelog.md`
- [ ] `../cli-catalog/schema/cli.schema.json`

## Schema

- [ ] `python3 -m cli_catalog validate` passes.
- [ ] The catalog follows `schema/cli.schema.json`.
- [ ] The schema source or schema version is recorded.
- [ ] Unknown values are marked explicitly.
- [ ] No field is filled with unsupported guesses.

## Research Quality

- [ ] Tools are within the agreed research scope.
- [ ] Non-CLI products are excluded or clearly marked.
- [ ] Duplicate tools are merged or explained.
- [ ] Each factual claim has a source trail where practical.
- [ ] Major uncertainty is documented.

## CCCC Handoff

- [ ] The handoff identifies `cli-summary.json` as the downstream scan index.
- [ ] The handoff identifies `catalog/data/*.json` as full canonical records.
- [ ] The handoff names the actual fields the ideation actor should use.
- [ ] The handoff states what the ideation actor should not assume.
- [ ] The leader can assign stage 2 without rereading the whole research
  process.
