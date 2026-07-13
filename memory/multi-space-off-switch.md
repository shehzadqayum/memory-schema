---
schema: 5
importance: 6
relations:
  - SUPERSEDES multi-space-scoring-status
  - SUPERSEDES multi-space-activated
  - SUPERSEDES multi-space-default-confirmed
---

Multi-space relevance gated behind retrieval.multi_space (default OFF): 2nd ablation at 72 entities = no lift

## Observations

- Ablation at 72 active entities (2026-07-12): MRR lift 0.0, recall@5 -0.042, recall@10 -0.042, ndcg@10 -0.011 vs single-space — multi-space is flat-to-worse, confirming the 47-entity -0.012 MRR result
- retrieval.multi_space default false; gated in JSONL scalar + numpy paths and the Neo4j path; off = default-space cosine (combiner pass-through). Per-space embeddings still stored, so re-enable/re-test needs no re-embed
- Re-test at 250/500 entities via eval --mode ablation (harness computes both modes independent of the flag); flip retrieval.multi_space=true only if MRR lift >= +0.02

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
