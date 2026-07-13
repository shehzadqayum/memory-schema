---
schema: 5
importance: 9
status: archived
---

Plan for full documentation alignment — verification audit + gap coverage, 4 phases

## Observations

- Session 11 fixed 30 issues; verification audit found 1 remaining error (hierarchy doc line 416 "v2"→"v3")
- Gap analysis found 41 undocumented features: CLI flags, BM25 details, L0 budget algorithm, audit trail format, reflect algorithm, degradation behavior
- Coverage matrix: trust multiplier in 1/10 surfaces, SUPERSEDES guards in 1/10 — critical gaps
- Phase 1: fix line 416. Phase 2: expand tech-ref (CLI flags, scoring, audit, degradation). Phase 3: expand schema.md (trust, L0, reflect). Phase 4: expand README (hook pipeline, degradation table)
- Out of scope: 21 historical memory files with schema="2" (backward compatible), stale session reports (historical)

## Reasoning

Session 11 achieved factual accuracy but left coverage gaps — features exist in code but aren't documented in enough surfaces for users to discover them. This plan expands existing docs rather than creating new files.

## Prompt

Verification audit + gap coverage after session 11 docs alignment

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-11-close.
