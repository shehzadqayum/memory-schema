---
schema: 5
importance: 9
relations:
  - MODIFIES chain-entity-design
  - MODIFIES chain-pattern-formalized
---

Live chain entity: created if absent, updated every response, released at end of cycle

## Observations

- Live chains grow through upsert append semantics — each response adds a step observation
- Upsert supports this: observations appended, description/reasoning replaced, relations merged
- Embedding re-computed on every update (hook fires on write) — chain embedding evolves as it grows
- Release at cycle end: finalize description/reasoning, add conclusion observation
- Changes mandatory write rule from "new entity per response" to "update active chain per response"

## Reasoning

This shifts chains from retrospective summaries to live accumulating records. The chain entity becomes a running log that grows with the session. Each upsert appends observations (the steps) while replacing the description (evolving summary) and reasoning (evolving narrative). The hook re-embeds on every write, so the chain's vector representation stays current. At release, the chain is a complete record of the reasoning sequence.

## Prompt

User proposed: chain created if absent, updated every memory event, released at end of cycle

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
