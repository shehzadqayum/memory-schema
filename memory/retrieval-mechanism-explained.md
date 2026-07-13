---
schema: 5
importance: 7
status: archived
---

Retrieval is explicit CLI call (memoryschema recall via Bash) — not neural, not implicit, auditable

## Observations

- Layer 1: LLM runs memoryschema recall via Bash tool before every response (rule-mandated)
- Layer 2: inside the call — embed query, score entries (recency+importance+relevance), variance-weighted combiner, cascade through relations/backlinks/k-NN
- Layer 3: LLM has no neural access to memories — they're not in weights or context window (except MEMORY.md index)
- Mechanism is retrieval-augmented: external store queried at response time, results injected into context
- If the LLM forgets to call recall, it doesn't have the memories — the rule is behavioral, not enforced by code

## Reasoning

The honest answer: it's a CLI call, not magic. The LLM runs a bash command, reads the output, and uses it. The sophistication is in what happens inside that command (7-space variance-weighted scoring, cascade), but the interface is a simple tool call. The memories are external, explicit, and auditable — not learned or implicit.

## Prompt

What is your memory retrieval mechanism?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
