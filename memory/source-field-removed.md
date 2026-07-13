---
schema: 5
importance: 7
---

Source field removed from framework — architecture is provenance and source agnostic

## Observations

- Removed source from: tags.py (parser), store.py (upsert merge), neo4j_store.py (props), consolidation.py (reflect), audit.py (diff fields)
- Removed from docs: schema.md (entity example, optional fields, upsert table), rules/memory-schema.md (entity example, optional fields)
- test_tags.py updated: removed source assertion from full_v2 test
- Backlink source (meaning source entity of a relation) is RETAINED — different concept
- Audit log_force source (meaning source entity of a force event) is RETAINED — different concept
- 669 tests passing after removal

## Reasoning

With provenance already removed, the source field was the last remnant of the origin-tracking system. The architecture now relies entirely on the basis attribute for trust (per-observation, epistemological) and the chain field for context grouping. No entity-level origin metadata remains.

## Prompt

Remove the source field — architecture is provenance and source agnostic

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
