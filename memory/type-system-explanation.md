---
schema: 5
importance: 4
status: archived
---

Explained how the type attribute works on memory entities

## Observations

- Type is an XML attribute on memory:entity — semantic, episodic, or procedural
- Type affects scoring: semantic has recency floor 0.6, episodic standard decay, procedural access-reinforced
- Type drives MEMORY.md progressive disclosure grouping (Knowledge, Session History, Procedures)
- Current corpus: 13 semantic, 23 episodic, 4 procedural out of 40 total

## Reasoning

The type system is already functional. The LLM sets type on every entity write. The question may be about whether the type selection is good or whether a different taxonomy would be better.

## Prompt

User asked how type currently works and whether the LLM specifies it

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
