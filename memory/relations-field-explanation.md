---
schema: 5
importance: 5
status: archived
---

The relations field: container of typed links to other memories, merged on upsert, not embedded

## Observations

- Each relation has target (memory name) and type (one of 7 relation types)
- Upsert: merged with deduplication (same target+type not duplicated)
- compute_backlinks() creates reverse links on target entities
- Not an embedding space — relations are structural (name + type), not semantic text
- Traversed in recall cascade graph walk, not via vector similarity

## Reasoning

Relations are the graph edges of the memory system. They're authored as forward links, computed as backlinks, and traversed during recall. They're distinct from embedding spaces — they encode explicit connections between memories rather than semantic content. The deduplication on merge prevents relation bloat on upsert.

## Prompt

Explain the relations field

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
