---
schema: 5
importance: 6
status: superseded
key: memory-schema.multi-space-status
valid_from: 2026-07-04
superseded_at: 2026-07-12
superseded_by: multi-space-off-switch
relations:
  - USES plan-memory-direction-2026
  - SUPERSEDES seven-space-scoring-activated
---

Multi-space scoring: measured NEGATIVE lift at this scale; still active in code (no off-switch); re-test at 100 entities

## Observations

- Ablation at 47 entities: multi-space vs single-space MRR delta -0.012, below the pre-committed +0.02 keep threshold — verdict keep DORMANT
- No config flag exists: multi_space_relevance runs unconditionally in both stores whenever an entry carries the embeddings dict — 'dormant' was aspiration, not code (found in the step-70 deep evaluation)
- The 2026 frontier research (plan-memory-direction-2026) frames it as a non-investment: no literature support for field-level multi-vector at any scale; re-run the ablation at corpus milestones 100/250/500 before deciding to build the off-switch or remove the machinery

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
