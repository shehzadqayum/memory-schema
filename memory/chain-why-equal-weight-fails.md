---
schema: 5
importance: 8
status: archived
relations:
  - USES multi-space-cross-similarity
  - USES query-conditioned-weighting-design
---

Chain: equal-weight multi-space averaging dilutes retrieval — proven through 4 experiments

## Observations

- Step 1: M1 built 3 field spaces (observations, reasoning) with equal-weight combiner
- Step 2: 3-space eval showed nDCG 0.601 vs single-space 0.608 — slight regression
- Step 3: Added description space (4th). 4-space nDCG dropped to 0.557
- Step 4: Added prompt space (5th). 5-space nDCG dropped to 0.555
- Step 5: desc+default weighted profile achieved nDCG 0.747 — beating all equal-weight configs
- Conclusion: the spaces have value but the combiner must weight them, not average equally

## Reasoning

Each experiment added a space and measured the result. The monotonic degradation (0.608 → 0.601 → 0.557 → 0.555) proved the combiner is the bottleneck. The desc+default weighted profile (0.747) proved the spaces themselves are valuable when weighted correctly.

## Prompt

Why does adding more embedding spaces make retrieval worse?

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: USES four-space-eval-results, USES five-space-eval-results.
