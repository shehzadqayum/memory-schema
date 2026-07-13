---
schema: 5
type: procedural
importance: 7
status: archived
---

Multi-space embedding activated in hook — all writes now embed in 3 spaces

## Observations

- Hook modified to embed default + observations + reasoning spaces on every write
- Verified: all 3 spaces produce distinct 1024-dim vectors with cross-space sim 0.66-0.87
- Field spaces skip gracefully when text is empty (structural absence)
- Trade-off: 3 Voyage API calls per write instead of 1 (~4.8s vs ~1.6s)

## Reasoning

The M1 infrastructure was built but only used the default space in the hook. Now all three spaces are populated on every write, giving richer semantic representation even though multi-space scoring was NO SHIP for default ranking.

## Prompt

User requested implementing and activating multi-space embedding per write

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
