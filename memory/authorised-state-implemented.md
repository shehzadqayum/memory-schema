---
schema: 5
importance: 9
---

Implemented authorised/unauthorised memory states — only active chain is writable

## Observations

- chain_state.py: get/set/release active chain via memory/.active_chain file
- Hook blocks upsert to existing memories unless name matches active chain
- CLI: memoryschema chain status/start/release
- New memories always allowed. Only upserts to existing names are gated.
- At most ONE authorised entity at any time. Release makes it read-only permanently.
- 681 tests passing, 11 new chain state tests

## Reasoning

The implementation uses a file-based singleton (memory/.active_chain) rather than a field on the entity because authorisation is a system-level state, not an entity property. The hook checks this file before allowing upserts. New writes are always allowed — only mutations to existing entities are gated.

## Prompt

Implement authorised/unauthorised memory states

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
