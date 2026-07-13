---
schema: 5
importance: 7
status: archived
---

Full memory system explanation: 7 spaces, variance-weighted combiner, authorised/unauthorised states, chain entities

## Observations

- 7 embedding spaces: 1:1 field-to-space mapping (name, description, observations, prompt, reasoning, chain) + default blend
- Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no heuristics, data determines weights
- Two memory states: unauthorised (read-only, default) and authorised (active chain only, one at a time)
- Write pipeline: authorisation check → parse → embed 7 spaces → divergence profile → gate 6 stages → store → MEMORY.md
- Chain entities: start (authorise) → update (upsert) → release (read-only permanent). Chain field enables grouping via vector similarity.
- 81 entries, 69 active, 7 spaces, 79 relations, 800 associations, 681 tests

## Reasoning

The system is architecturally complete: every field maps to an embedding space, divergence profiles enable self-regulating weight, authorisation gates enforce immutability with a single writable chain exception, and the full pipeline runs automatically on every write via the PostToolUse hook.

## Prompt

Explain how our memory system works

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
