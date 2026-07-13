---
schema: 5
importance: 9
---

Automatic recall implemented: rules mandate memoryschema recall before every response

## Observations

- Added to memory-working.md: "Before answering ANY user question, recall relevant memories"
- Pattern: user asks → LLM recalls (memoryschema recall via Bash) → uses context → responds → writes memory
- Skip only for mechanical operations (git commits, file staging)
- Closes the write-only loop identified in recall-not-used finding
- First rule-mandated recall demonstrated: recall-not-used (0.774) and recall-example (0.735) retrieved

## Reasoning

The most important finding of the session was that the system never recalled memories during responses — it was write-only. Adding the recall mandate to the rules file (loaded into every conversation) ensures future sessions use the captured knowledge. The recall is a real retrieval operation via memoryschema recall, not file reading.

## Prompt

Implement automatic recall before every response

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
