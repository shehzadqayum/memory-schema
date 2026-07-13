---
schema: 5
importance: 9
---

A chain of reasoning is a sequence of memory events with a defined start (trigger) and end (conclusion)

## Observations

- Each step in the chain is a memory entity connected to the next in sequence
- The framework has entities, relations, prompt (trigger), reasoning (thinking), observations (facts) — all pieces exist
- Missing: the chain as a first-class concept — no way to group memories into an ordered sequence with start/end
- Three design options: chain entity (meta-memory), new relation type (NEXT_STEP), or chain attribute (shared ID + step number)

## Reasoning

The current relation types (DEPENDS_ON, INFORMS) connect memories but don't imply sequential ordering. A chain needs ordering — step 1 before step 2 before step 3. The representation must capture both the sequence and the chain boundary (where it starts and ends).

## Prompt

User defined: a chain of reasoning is a sequence of memory events with a start and an end

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
