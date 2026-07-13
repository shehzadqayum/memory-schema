---
schema: 5
importance: 7
status: archived
---

Neo4j upsert could not append observations to a node whose observations property was NULL (the dedup filter short-cir…

## Summary

Neo4j upsert could not append observations to a node whose observations property was NULL (the dedup filter short-circuited); fixed with coalesce, and the 4 seed entities it had silently stranded were repaired (2026-06-24).

## Observations

- BUG (neo4j_store.py upsert): the observation-merge Cypher did 'WITH m, m.observations AS existing' then '[x IN $observations WHERE NOT x IN existing]'. When m.observations was NULL (nodes first created as bare relation-MERGE stubs rather than via ON CREATE), 'x IN null' yields null, 'NOT null' is null, so every observation was filtered out and m.observations stayed null. Observations could be set ON CREATE but never APPENDED on a later ON MATCH to a null-observations node.
- FIX: 'WITH m, coalesce(m.observations, []) AS existing' — a null becomes an empty list so the dedup-append works. One-line change; added an integration regression test in test_neo4j_store.py (create a bare node, upsert observations, assert they persist).
- IMPACT: four early seed entities (trading-journal-overview, usd-strength-20260619, chart-selection-criteria, account-rdd-waterline) had their observations only in their .md files (4/3/7/5 obs) but ZERO in the Neo4j/JSONL projection, plus null created_at. Their embeddings had been built from name+description only (no observations space), weakening recall on observation-only content.
- REPAIR: targeted re-index of just those 4 (parse_memory_file then embed_all_spaces then store.upsert) AFTER the coalesce fix; created_at backfilled from last_accessed where null. Verified: zero-obs entities 4 to 0, null created_at 4 to 0, total observations 131 to 150, avg spaces/entry 4.33 to 4.67, each gained the observations-space embedding. Deliberately did NOT run a full 'memoryschema index' (that re-upserts every .md and would have reverted the seven-space-scoring-dormant supersession, since its .md has no status attribute). doctor 22/22, no test/imported pollution.
- LESSON: the earlier integrity audit's '13 JSONL = 13 Neo4j nodes, validate clean' verdict did NOT catch this — validate checks .md file STRUCTURE and node COUNTS, not field-level store-vs-markdown projection completeness. A future deeper health check should compare per-entity observation counts between the .md files and the store. This is a vendored-package fix — re-apply on re-vendor.

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
