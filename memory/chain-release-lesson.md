---
schema: 5
type: procedural
importance: 8
status: archived
---

Release chains when the topic concludes — don't accumulate indefinitely into one entity

## Observations

- chain-implementing-live-chains accumulated 141 observations across many topic shifts — became incoherent
- Each topic shift should have triggered a release and new chain or standalone memory
- Editing a prior released memory violates the chain lifecycle: create → update → release → new
- A chain with more than ~10-15 observations has likely missed its release point

## Reasoning

The user caught a behavioral error: I was continuously upsetting one chain entity across multiple distinct topics instead of releasing it and starting new memories. The chain lifecycle rule exists for exactly this reason — a chain should capture ONE coherent reasoning sequence, not become an ever-growing log.

## Prompt

Why are you editing a prior memory?

## Chain

learning to use the memory system correctly

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
