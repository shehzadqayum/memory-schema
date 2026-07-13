---
schema: 5
type: procedural
importance: 8
---

Memory write enforcement changed from selective to mandatory on every response

## Observations

- Rules updated: memory-working.md now requires a memory entity at the end of every response
- Write decline instrumentation section removed since writes are no longer optional
- Hook pipeline verified: parse, embed (1024-dim Voyage), gate, JSONL store, MEMORY.md update all working

## Reasoning

The user wants every response to produce a vector-embedded memory entity. This exercises the full write pipeline continuously and builds a comprehensive session record. The trade-off is ~1.6s Voyage API latency per response.

## Prompt

User requested removing testing mode qualifier and making mandatory memory write the default

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
