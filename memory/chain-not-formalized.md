---
schema: 5
importance: 6
status: archived
---

Chain entity pattern is working but not documented in schema rules, design docs, or working memory guidelines

## Observations

- Pattern exists only as ad-hoc memories and conversation knowledge — no formal spec
- Needs documentation in: .claude/rules/memory-schema.md, docs/schema.md, .claude/rules/memory-working.md
- Three locations needed: schema (what a chain entity looks like), working guidelines (when to create one), design docs (the pattern rationale)

## Reasoning

The pattern works empirically (3 chains tested, recall scores 0.72-0.78) but isn't codified. Without formalization, future sessions won't know the pattern exists or how to apply it. The schema rules and working guidelines are loaded into every conversation — adding chain guidance there ensures it persists.

## Prompt

User asked if chain entity pattern has been documented and formalized

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
