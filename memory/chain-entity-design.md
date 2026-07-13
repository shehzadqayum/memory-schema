---
schema: 5
importance: 9
---

Chain entity design: a meta-memory listing ordered steps as observations with USES relations to evidence

## Observations

- A chain entity is a regular memory entity — no schema changes needed
- Steps are listed as ordered observations: "Step 1: ...", "Step 2: ...", "Conclusion: ..."
- USES relations link the chain to the individual evidence memories
- The chain has its own prompt (trigger question), reasoning (why the chain matters), description (summary/conclusion)
- Chain entities are embeddable in all 5 spaces — findable by the trigger question, the conclusion, or any step
- Recall cascade follows USES relations to surface the full evidence set from the chain

## Reasoning

The chain entity pattern requires zero schema changes — it uses existing entity structure, observations for ordered steps, and USES relations for evidence linking. The chain itself becomes a semantic summary that persists (recency floor 0.6) while the individual evidence steps may be episodic and decay. This creates a natural knowledge distillation pattern.

## Prompt

User chose chain entity approach for representing reasoning chains

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
