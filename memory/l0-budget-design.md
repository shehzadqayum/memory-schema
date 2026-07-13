---
schema: 5
importance: 6
---

MEMORY.md L0 budget: 2000 tokens max, evicts lowest-scoring entries, groups by type

## Observations

- Token estimation: chars / 4 (conservative approximation)
- Eviction order: score-based if store available (lowest importance+recency first), FIFO otherwise
- Progressive disclosure: entries grouped under Knowledge, Procedures, Session History headers
- Evicted entries persist in L1+ stores — only L0 index visibility is removed
- L0 gating: ingested provenance entries never enter MEMORY.md (security boundary)

## Reasoning

L0 is the always-in-context index. It must stay small enough to fit in the prompt without crowding out working space. The budget enforcement ensures the index grows bounded while keeping the highest-value entries visible.

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
