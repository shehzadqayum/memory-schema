# Resolve Residuals: JSONL/Neo4j Sync (COMPLETE)

## Context

The JSONL store has 34 entries, Neo4j has 36 nodes. The 2 extra Neo4j entries (`imported` and `test`) are orphaned test data from prior development — they have no status field and are not real memory entities. Syncing them to JSONL would pollute the store. The fix is to delete them from Neo4j and verify alignment.

## Prior Residuals (from [S4] 321e183)

- JSONL/Neo4j count mismatch: 34 vs 36 → addressing in Phase 1

## Phase 1 — Sync JSONL and Neo4j stores ✓ d8dad45

### 1.1 Delete orphaned Neo4j entries
- Delete `imported` and `test` from Neo4j: `memoryschema delete imported` and `memoryschema delete test` (with NEO4J_PASSWORD=changeme)
- These are test artifacts, not real memory entities

### 1.2 Verify sync
- Run `memoryschema sync` — should show 34/34, "in sync"
- Run `memoryschema neo4j status` — should show 34 nodes

### 1.3 Add sync verification test
- Add to `tests/test_e2e_pipeline.py` or existing test: verify that after upsert to both stores, counts match
- Optional: if too narrow for a dedicated test, skip and rely on operational verification

### Key files
- `src/memoryschema/cli/migrate_cmd.py` — sync command
- `src/memoryschema/cli/memory_cmd.py` — delete command

**Verification:** Operative (memoryschema sync shows 34/34 in sync)

## Verification Criteria

| # | Criterion | Phase | Status type |
|---|-----------|-------|-------------|
| 1 | Neo4j orphans deleted, sync shows 34/34 | 1 | Operative |
