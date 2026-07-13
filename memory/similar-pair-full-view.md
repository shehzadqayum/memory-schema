---
schema: 5
importance: 4
status: archived
---

Full view of most similar pair: sequential eval experiments, 5 spaces each, no divergence profiles

## Observations

- Both have 5 embedding spaces (predate name and chain spaces), no divergence profiles, no confidence, no chain field
- Same 2 backlinks (both USES targets of the same 2 chain entities)
- Top k-NN neighbor of each is the other (0.939 mutual)
- Content differs in specific numbers (0.557 vs 0.555) and experiment stage (4 vs 5), but structure identical
- These entries would benefit from reembedding with all 7 spaces + divergence profiles

## Reasoning

The full view reveals that older entries lack the newer features (chain field, name space, divergence profile). A reembed pass across all entries would bring the entire corpus to the current 7-space architecture with divergence profiles, enabling the variance-weighted combiner to work on every entry.

## Prompt

Show both memories in full

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
