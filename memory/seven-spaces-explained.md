---
schema: 5
importance: 7
status: archived
---

Why 7 spaces: each field embedded independently so queries can match intent, facts, topic, or rationale separately

## Observations

- Most systems: 1 vector per entry (all text blended). This system: 7 vectors (one per field + default blend).
- Benefit: "what did the user ask?" matches prompt space, "what facts exist?" matches observations space — different queries activate different fields
- Description diverges from default by 0.21-0.35 — captures what's actually different between topically similar entries
- Variance-weighted: divergence from default IS the weight. Distinctive fields amplified (prompt at 0.60 weight), redundant fields suppressed (observations at 0.08)
- 7 × 1024 = 7168 dimensions per entry — more storage and compute, but enables field-level discrimination

## Reasoning

The multi-space architecture exists because a single blended vector loses field-level information. When everything is mixed into one vector, you can't tell whether a query matched the user's intent, the observed facts, or the rationale. Separate spaces preserve this distinction. The variance-weighted combiner then decides at query time which fields matter most for each specific query-entry pair.

## Prompt

Explain 7 independent spaces per entry

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
