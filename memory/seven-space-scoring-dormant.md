---
schema: 5
importance: 7
status: superseded
---

memory-schema's 7-space variance-weighted scoring is fully coded but DORMANT in Helios…

## Summary

memory-schema's 7-space variance-weighted scoring is fully coded but DORMANT in Helios: Neo4j persists only the single 'embedding', so recall runs single-space — and on the small corpus it gives zero lift anyway.

## Observations

- The hook (hook-post-write.sh) computes all 7 spaces (default + name/description/observations/prompt/reasoning/chain) plus a divergence_profile (= 1 minus cosine-to-default), but neo4j_store.py never persists 'embeddings'/'divergence_profile' — only 'embedding'. Verified 2026-06-24: every node, incl. the chain edited 6x that day, carries single-vector only.
- migrate neo4j-to-jsonl exports Neo4j's single-vector view, so store.jsonl is single-space too. Both backends therefore call combine_similarities with one space, which returns the default cosine directly. Recall in this deployment is single-space.
- Ablation (13-entity corpus, 6 Helios queries with gold targets, 7 spaces reconstructed in-memory via compose_embedding_text + embed_batch): single-space AND 7-space both scored MRR 1.000, mean rank 1.00, 6-of-6 top-1. 7-space gave ZERO lift and occasionally slightly lower gold-similarity (it averages in lower-sim field spaces).
- Why no lift: tiny, topically-distinct corpus (single-space is already perfect — nothing to re-rank) plus low inter-space divergence on short entities (e.g. RDD entry: description divergence 0.017 = near-duplicate of default; name 0.29). The default space is pinned at weight 1.0 and dominates.
- The design is principled and pays off at SCALE — many near-duplicate entities and long, distinct fields where a specific field disambiguates an ambiguous default blend. For Helios as-is it is both unnecessary and inactive; single-space suffices. Fully activating it needs a neo4j_store change to persist the embeddings dict + divergence_profile (plus a re-embed).

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
