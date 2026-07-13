---
schema: 5
importance: 6
status: archived
---

Added description embedding space — 4 spaces now active per entry (4096 total dims)

## Observations

- Description space added to embedding_input.py, spaces.py registry, and hook-post-write.sh
- All 53 entries reembedded in description space — 46 have all 4 spaces, 7 have 3 (no reasoning)
- Description space isolates the one-line summary — high discriminative power (0.35-0.47 gap from default on similar entries)
- 4 new tests added for description space composition (empty, truncation, content isolation)

## Reasoning

Empirical analysis showed entries with high default similarity (0.70-0.83) had description similarity as low as 0.32. The one-line summary captures compressed topic identity distinct from observation facts and reasoning rationale. Added as the 4th space alongside default, observations, reasoning.

## Prompt

User approved adding description space after evaluation showed high discriminative value

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
