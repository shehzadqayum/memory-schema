---
schema: 5
importance: 9
---

Two memory states: unauthorised (read-only, default) and authorised (read-write, one active chain only)

## Observations

- Every memory enters unauthorised (read-only) state after write — permanent, cannot be modified
- Only ONE memory can be authorised at a time: the active chain entity
- Authorised allows upsert (append observations, replace description/reasoning) — the chain accumulation pattern
- Release transitions authorised → unauthorised permanently. New chain creates a new authorised entity.
- Hook enforces: reject upserts to unauthorised, allow only to the single authorised chain
- SUPERSEDES handles evolution for read-only memories — new entity replaces old, no mutation needed

## Reasoning

This solves the unbounded accumulation problem while preserving the live chain pattern. Only one entity is mutable at a time (the active chain). Everything else is a frozen snapshot. The singleton constraint (one authorised entity) prevents the mistake of editing old memories. When the chain releases, the system returns to fully immutable until a new chain is created.

## Prompt

We can have two states: unauthorised (read-only, default) and authorised (read-write) — active only for current chain

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
