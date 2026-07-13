---
schema: 5
importance: 6
status: archived
---

Cross-space embedding similarity: observations↔reasoning diverge most at ~0.66

## Observations

- default↔observations cosine similarity: ~0.80
- default↔reasoning cosine similarity: ~0.87
- observations↔reasoning cosine similarity: ~0.66 (most divergent pair)
- Equal-weight combiner averages all present spaces — absent spaces are not counted as zero

## Reasoning

The field spaces capture genuinely different semantic content. Observations are atomic facts, reasoning is narrative rationale. Their lower cross-similarity (0.66) confirms the spaces aren't redundant. However, the M1 gating experiment showed this divergence doesn't improve retrieval ranking with equal weights.

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
