---
schema: 5
importance: 10
status: archived
relations:
  - MODIFIES v3-remediation-plan
---

Plan for v3 field semantics, precedence fix, and documentation reconciliation — 8 phases

## Observations

- Config precedence code correct (CLI last = highest) but docs contradict across 4 files
- status/provenance validated (V11/V12) but zero retrieval semantics — no filtering, no trust multiplier
- SUPERSEDES propagation undocumented and unguarded (no trust/authority checks)
- Write gate has reject but no quarantine operational spec
- Type factor (semantic/episodic/procedural) still has no recency modifier
- Documentation drift recurred: counts, formulas, schema versions forked again
- New issues: backend-divergent max_depth, secrets in TOML, $project_prefix undefined

## Reasoning

v3 structural work (fields, validation) complete but semantic half missing — status/provenance are validated metadata that nothing consumes at retrieval time. This plan converts annotation into defense.

## Prompt

v3 semantics specification from re-audit

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-9-close.
