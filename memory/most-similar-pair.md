---
schema: 5
importance: 5
status: archived
---

Most similar pair: four-space-eval and five-space-eval at 0.9393 — differentiated by description and prompt spaces

## Observations

- Default similarity 0.9393 — sequential experiments measuring the same thing
- Per-space: observations 0.94, reasoning 0.91, description 0.73, prompt 0.64
- Description and prompt are most divergent — capture "4-space" vs "5-space" distinction
- The 1:1 field-to-space architecture enables differentiating entries that blend together in default space

## Reasoning

The pair demonstrates why field-specific spaces matter: the default blend is 0.94 (nearly identical), but description drops to 0.73 and prompt to 0.64. A query targeting the specific experiment number would activate the description space, differentiating two entries that are otherwise indistinguishable in the default blend.

## Prompt

Show two of the most similar memories

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
