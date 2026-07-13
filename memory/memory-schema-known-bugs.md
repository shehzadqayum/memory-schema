---
schema: 5
importance: 7
status: superseded
---

Three latent bugs found in the vendored memory-schema package on 2026-06-24 (NOTED to fix, not yet fixed)…

## Summary

Three latent bugs found in the vendored memory-schema package on 2026-06-24 (NOTED to fix, not yet fixed): JSONL chain-reasoning doubling, supersession-revert on re-index, and superseded entries dropped from JSONL export. None currently bite (Neo4j is the active backend; live store verified clean).

## Observations

- BUG-1 (latent, medium): the JSONL store (store.py _upsert_inner) APPENDS reasoning for chain- entities ('existing' + separator + 'new'), but the .md file already holds the FULL accumulated reasoning, so a re-index or a Neo4j-to-JSONL failover DOUBLES it (verified on a temp store: re-upserting the same reasoning yields it twice). The Neo4j store REPLACES reasoning (props whitelist) so it is correct, and the live chain is clean (28 distinct step markers, zero duplicates). The two backends are INCONSISTENT. FIX: make the JSONL store REPLACE chain reasoning like Neo4j (drop the chain- append special-case), or dedup on append.
- BUG-2 (latent, medium-high): a full 'memoryschema index' REVERTS supersession. parse_memory_file returns status='active' for a status-less .md (status is store-managed, never written into the .md), and upsert then overwrites a superseded node back to active (verified on a temp store). This is why the 2026-06-24 seed repair used a TARGETED re-index of only the 4 affected entities rather than a global index. FIX: the parser should return status=None when the .md has no status attribute (so upsert skips it and preserves the store's status), or upsert should refuse to downgrade superseded to active without an explicit 'active' in the source.
- BUG-3 (latent, low-medium): migrate neo4j-to-jsonl exports via list_all() (active-only), so superseded entities DROP from store.jsonl (e.g. seven-space-scoring-dormant lives in Neo4j and its .md but not in the JSONL export — JSONL shows 15 of 16 nodes). The .md remains source of truth, but a jsonl-to-neo4j rebuild would lose superseded nodes, and a later 'index' from the .md files would resurrect them as active (compounds BUG-2). FIX: export with include_inactive=True, preserving status.
- MINOR: (a) 'memoryschema embed --coverage' counts only the single 'embedding' field, not multi-space coverage (cosmetic; all nodes have the default vector so coverage still reads 100 percent). (b) neo4j_store._deserialize_multispace drops field spaces if the default vector is missing (no anchor) — only reachable for a manually-malformed entry, since embed_all_spaces always sets default. All bugs are in the VENDORED package, so any fix is a local patch to re-apply on re-vendor and should ship with a regression test (like the null-observations fix did).

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
