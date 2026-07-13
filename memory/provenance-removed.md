---
schema: 5
importance: 9
---

Provenance removed from entire framework — code, tests, and documentation synchronized

## Observations

- Removed from config.py: VALID_PROVENANCES, TRUST_LEVELS constants
- Removed from tags.py: provenance attribute parsing
- Removed from validator.py: V12 (provenance validation), V13 (ingested requires source)
- Removed from write_gate.py: stage 2 (provenance admission), stage 3 (provenance mismatch guards) — gate is now 4 stages
- Removed from store.py: trust multiplier in scoring, trust guard in SUPERSEDES. Verification guard (basis-based) retained.
- Removed from neo4j_store.py: trust guard, trust multiplier, provenance in upsert
- Removed from hook: L0 provenance gating (all memories now enter MEMORY.md)
- Removed from docs/schema.md: provenance semantics section, trust hierarchy, L0 gating, V12/V13 rules
- Removed from .claude/rules/: provenance field, trust references, gate stage count updated
- 8 test methods removed, 669 tests passing
- Trust is now handled by basis attribute (per-observation, epistemological) not provenance (per-entity, categorical)

## Reasoning

Provenance introduced false trust granularity — 4 values mapped to effectively 2 trust levels (trusted=3 vs ingested=1). The basis attribute on observations provides better per-observation trust grounding (measured/inferred/reported). Removing provenance simplifies the framework: fewer gate stages, no trust multiplier, no L0 gating by content origin. The verification guard (basis-based SUPERSEDES check) is retained as the correct trust mechanism.

## Prompt

Remove provenance from the entire framework

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
