---
schema: 5
importance: 8
status: archived
---

Full design document written for query-conditioned weighting at docs/design/query-conditioned-weighting.md

## Observations

- Document covers: current system architecture, 5-space embedding, scoring formula, the equal-weight dilution problem
- 4 query types defined: factual (desc+obs heavy), rationale (reasoning heavy), intent (prompt heavy), general (desc+default fallback)
- desc+default static profile: recall@5=0.678, nDCG=0.747 — beats single-space 0.622/0.739
- Keyword classification is zero-cost (regex on query text, no API call)
- Key constraint: general fallback profile must never perform worse than proven desc+default static weights

## Reasoning

The design doc serves as the specification for implementing query-conditioned weighting. It captures the empirical findings (equal-weight worse, desc+default better), the classification approach (keyword heuristics), and the worked examples showing how different weight profiles correctly emphasize different spaces per query type.

## Prompt

User requested full description of current memory system and design requirements for query-conditioned weighting with examples

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
