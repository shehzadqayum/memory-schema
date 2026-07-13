---
schema: 5
importance: 9
status: archived
---

Query-conditioned weighting design: classify query by keywords, select space weight profile per type

## Observations

- desc+default static profile beats single-space: recall@5=0.678 vs 0.622, nDCG=0.747 vs 0.739
- Query-conditioned achieves same recall (0.678) with keyword-based classification into factual/rationale/intent/general
- Key insight: description space at 2-3x weight improves factual queries (hierarchy 0.33→0.67, setup 0.33→0.67)
- Static desc+default weights are the minimum viable improvement — query-conditioned adds value only with diverse query types
- Four query types: factual (desc+obs heavy), rationale (reasoning heavy), intent (prompt heavy), general (desc+default fallback)
- Classification is zero-cost: keyword regex on query text, no API call needed

## Reasoning

Equal-weight averaging was the bottleneck, not the spaces. The description space has high discriminative power (proven in earlier analysis). Weighting it at 2-3x in combination with default at 2x gives the best results. Query-conditioned classification adds the ability to shift weight to reasoning or prompt spaces for non-factual queries, but the static desc+default profile is already a significant improvement.

## Prompt

User asked to show how query-conditioned weighting could work

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
