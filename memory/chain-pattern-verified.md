---
schema: 5
type: procedural
importance: 8
---

Chain entity pattern verified: chains surface as top result, cascade follows USES to evidence

## Observations

- Chain entities score 0.72-0.78 for their trigger questions — highest among all results
- USES relations pull evidence memories into recall results via cascade (depth 1-2)
- Three chains created and tested: equal-weight-fails, hook-investigation, memory-quality-evolution
- Chain observations provide the ordered summary; cascade provides the detailed evidence
- Pattern requires zero schema changes — uses existing entity structure, observations for steps, USES for evidence

## Reasoning

The chain entity is a semantic memory (recency floor 0.6, persists) that embeds the full reasoning sequence in its observations and links to evidence via USES. When recalled, it surfaces as the top result and the cascade pulls in supporting memories. This creates a knowledge distillation pattern: individual episodic steps may decay, but the chain persists as a semantic summary with links back to evidence.

## Prompt

Do chain entities work with recall cascade?

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
