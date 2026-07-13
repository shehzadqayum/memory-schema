---
schema: 5
importance: 5
status: archived
---

Documentation synchronized with authorised/unauthorised memory state model

## Observations

- docs/schema.md: authorisation gate in upsert semantics, chain lifecycle with CLI commands, behavioral spec updated
- .claude/rules/memory-schema.md: Rule 6 authorisation gate + chain field, Rule 9 start/release lifecycle
- .claude/rules/memory-working.md: lifecycle with commands, .active_chain file, standalone memories read-only

## Reasoning

The authorisation model was implemented in code but absent from all documentation. Three files updated: source of truth (schema.md), derived rules, and working guidelines. Authorisation is now documented as a prerequisite for upsert throughout the write pipeline.

## Prompt

Synchronise all documentation with authorised/unauthorised implementation

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
