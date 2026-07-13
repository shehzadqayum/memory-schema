---
schema: 5
importance: 8
status: archived
---

Plan for full v3 documentation alignment — 15 findings, 7 fix items, 8 files

## Observations

- Documentation stuck at v2 while implementation is v3
- Missing: status/provenance attributes, V11/V12/R6 rules, PARENT_OF/CHILD_OF deprecation
- Working memory policy contradicts implementation: docs say every-response, impl is selective-write
- Test count stale (390→432), doctor count inconsistent (18/20/21→21)
- 5 modules missing from technical reference

## Reasoning

Exhaustive audit across all documentation surfaces — user-facing docs, rules, templates, CLI docstrings, README, CHANGELOG. Root cause: v3 implementation completed in session 7 but docs not updated.

## Prompt

audit all documentation and bring into alignment with implementation

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-8-close.
