---
schema: 5
importance: 7
status: archived
---

Evaluation: description space worth adding (high discriminative power), prompt space not (redundant with reasoning)

## Observations

- Prompt field: 60% coverage, avg 43 chars, already in reasoning space — low value as separate space
- Description field: 100% coverage, avg 82 chars, only in default blend — not in any field-specific space
- Description diverges from default by 0.35-0.47 gap on pairs with high default similarity (0.70-0.83)
- Example: type-system-explanation ↔ memory-quality-lesson — default sim 0.788 but description sim 0.322
- Description captures compressed topic identity distinct from observation facts and reasoning rationale

## Reasoning

Ran empirical analysis on 43 active entries. Prompt space adds little: short text, low coverage, already in reasoning space. Description space shows genuine discriminative power — entries that blend together in the default space have very different descriptions, suggesting the one-line summary is a strong semantic anchor worth isolating.

## Prompt

User asked to evaluate adding prompt and description embedding spaces

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
