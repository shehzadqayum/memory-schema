---
schema: 5
importance: 7
relations:
  - SUPERSEDES memory-schema-known-bugs
---

The 3 latent memory-schema bugs (chain-reasoning doubling, supersession-revert on re-index, superseded dropped from J…

## Summary

The 3 latent memory-schema bugs (chain-reasoning doubling, supersession-revert on re-index, superseded dropped from JSONL export) were FIXED + tested + verified live on 2026-06-24. Supersedes the known-bugs note.

## Observations

- FIX-1 (chain reasoning doubling): store.py _upsert_inner now REPLACES reasoning unconditionally (dropped the chain- append special-case), matching the Neo4j store and schema Rule 6/9. The .md file is the accumulator; the store mirrors the full text. Rewrote test_store.py test_chain_reasoning_appends to test_chain_reasoning_replaces. Verified: re-upserting the full text no longer doubles.
- FIX-2 (index reverts supersession): tags.py parse_memory_file no longer defaults status to 'active' (status = root.get('status')), and OMITS the status key from the parsed entity when absent (via dict-unpacking). So an upsert never overrides a server-managed superseded/archived status on a re-index. Omitting (not setting None) is required because dict.get('status','active') returns None for a present-but-None key, which would wrongly exclude new entities from list_all. Verified: parse of a status-less .md returns no status; re-upserting a superseded entity keeps it superseded; a status-less new entity is still listed as active.
- FIX-3 (superseded lost on export/rebuild): migrate_cmd.py neo4j_to_jsonl now uses list_all(include_inactive=True), and migration.py entry_to_node_props carries 'status'. Verified LIVE: migrate neo4j-to-jsonl now exports all 17 nodes (store.jsonl is a complete mirror including the superseded seven-space-scoring-dormant); a jsonl-to-neo4j rebuild preserves status.
- Regression tests added: test_status_supersession_fix.py (4 tests: parse omits status, status-less entity treated active, re-index does not revert supersession, migration carries status) + the rewritten test_chain_reasoning_replaces. VERIFIED: full mocked suite green, Neo4j integration green, doctor 22/22, no test/imported pollution, live store healthy (17 nodes). The 2 MINORs (embed --coverage multi-space; _deserialize_multispace default anchor) were left optional/not-done. All fixes are VENDORED — re-apply on re-vendor.

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
