---
schema: 5
importance: 7
status: superseded
superseded_at: 2026-07-04
superseded_by: multi-space-scoring-status
relations:
  - SUPERSEDES seven-space-scoring-dormant
---

The 7-space variance-weighted scoring is now ACTIVE in Helios (2026-06-24)…

## Summary

The 7-space variance-weighted scoring is now ACTIVE in Helios (2026-06-24): per-space vectors persist in Neo4j + JSONL, scoring is shared across both stores, all 14 entities backfilled. Still ~zero lift on the small corpus, by design.

## Observations

- Activated 2026-06-24, superseding the dormant state. Root gap fixed: neo4j_store.upsert now persists each non-default space as its own native float-array property (emb_ prefixed, e.g. emb_observations / emb_reasoning) plus divergence_profile as a JSON-string prop; _node_to_dict reconstructs entry embeddings + divergence_profile on read. The default vector stays in m.embedding for the existing memory_embedding vector index.
- Scoring is shared: store.multi_space_relevance is now a module-level wrapper, and Neo4j _score_entry routes through it (it previously used only the single embedding, so even persisted multi-space data would not have been scored). The JSONL upsert merge whitelist now keeps embedding/embeddings/divergence_profile, so re-upserted entries (especially the active chain) retain their multi-space data.
- Shared helpers spaces.compute_divergence_profile and spaces.embed_all_spaces consolidate the embed loop; the hook was refactored to call embed_all_spaces (no more inline math) so hook-written and backfilled profiles cannot drift. migration.py carries the per-space props in the jsonl-to-neo4j direction.
- Backfill: new CLI 'memoryschema embed --all-spaces' (reembed.reembed_all_spaces) re-embeds all entities across spaces + computes divergence and upserts to the configured store. Ran it: 14/14 backfilled; Neo4j has emb_ props on all 14 (10 carry emb_observations; entities without observations text compose fewer spaces), JSONL carries the embeddings dict + divergence on all 14.
- VERIFIED: 14/14 entries load with a live multi-space dict from Neo4j; multi-space scoring executed on 56 entry-scorings; doctor 22/22, no test/imported pollution; the full suite (plus a new tests/test_multispace_persistence.py) is green with .env loaded. As predicted and unchanged from the dormancy-era ablation, single-space and multi-space both score MRR 1.000 on this tiny topically-distinct corpus — activation is correct; lift stays zero until the corpus scales.
- Storage = per-space NATIVE float arrays (operator decision) to keep future per-space Neo4j VECTOR INDEXES possible for multi-space candidate selection at scale; today candidate selection stays default-space and multi-space is Python-side re-ranking. All edits are in the VENDORED package (spaces, store, neo4j_store, migration, reembed, index_cmd, hook + the new test) — re-apply on any package re-vendor, like the hook/conftest patches.

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
