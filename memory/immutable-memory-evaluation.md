---
schema: 5
importance: 9
status: archived
---

Evaluation: memories should be immutable after write — no upsert, no append, each memory a snapshot

## Observations

- Current upsert-append model lets observations pile up (141 in one entity) and descriptions get overwritten
- Immutable model: every response writes a NEW memory, chain entity written ONCE at release
- SUPERSEDES relation replaces old memories instead of mutation
- Chain lifecycle changes: standalone step memories during investigation, one chain entity at release, all immutable
- Simplifies everything: no merge conflicts, no observation bloat, no overwritten descriptions
- Divergence profile computed once at write time — never needs recomputation

## Reasoning

The upsert model was designed for incremental enrichment but in practice caused unbounded growth and incoherent entities. Immutable memories are simpler: each is a point-in-time snapshot with a fixed embedding and divergence profile. SUPERSEDES handles evolution — the new memory replaces the old rather than mutating it. The 7-space architecture and variance-weighted combiner work identically on immutable memories.

## Prompt

Any memory should remain read-only. Evaluate.

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
