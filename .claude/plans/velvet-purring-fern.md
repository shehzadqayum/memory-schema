# Framework Hardening: Test Gaps + Broken Paths (COMPLETE)

## Context

After completing the multi-space embedding experiment (M1, NO SHIP), a full framework audit revealed 7 gaps: hook parse errors blocking auto-memory writes, one untested module (l0_budget.py), no end-to-end pipeline test, broken Neo4j auth, a non-functional reflect command, an unresolved hook integration test residual (session 18), and mocked-only Neo4j tests. This plan fixes all of them in priority order.

## Prior Residuals (from [S4] d4043ce)

- Hook integration test: E2 write path Tested but not Operative via subprocess → addressing in Phase 6

## Phase 0 — Fix hook parse errors on non-entity files ✓ 8acfaec

The hook at `src/memoryschema/hooks/hook-post-write.sh` blocks writes to any `.md` file under a `/memory/` path that doesn't contain `<memory:entity>` XML. Auto-memory files (YAML frontmatter format) trigger this on every write, producing "failed to parse" errors and exit code 2.

**Root cause:** Lines 57-60 of the hook's Python block treat `parse_memory_file() → None` as a fatal error (exit 2). A file without `<memory:entity>` is not an error — it's a non-entity file that should be skipped.

### 0.1 Fix hook to skip non-entity files gracefully
In `hook-post-write.sh`, change the None-return handling:
```python
# BEFORE (lines 57-60):
memory = parse_memory_file(filepath)
if memory is None:
    print(f'hook: failed to parse {filepath}', file=sys.stderr)
    sys.exit(2)

# AFTER:
memory = parse_memory_file(filepath)
if memory is None:
    # Not a memory entity file (e.g., YAML frontmatter) — skip silently
    sys.exit(0)
```

### 0.2 Add test for non-entity file handling
In `tests/test_cli_hook.py` (or new test):
- `test_parse_returns_none_for_yaml_frontmatter` — write a YAML frontmatter .md file, call `parse_memory_file()`, verify returns None
- `test_parse_returns_none_for_plain_markdown` — plain markdown without entity block returns None

### Key file
- `src/memoryschema/hooks/hook-post-write.sh` — lines 57-60

**Verification:** Operative (auto-memory writes no longer produce hook errors)

## Phase 1 — l0_budget.py test coverage ✓ cbe8c83

The only module (out of 21) without dedicated tests. Token budget enforcement for MEMORY.md is critical — if it silently breaks, the L0 index grows unbounded.

### 1.1 Create tests/test_l0_budget.py
- `TestEstimateTokens`: empty string → 0, known length → chars//4
- `TestParseIndexEntries`: extracts `- [name](file.md)` entries, preserves other lines, handles empty content
- `TestEnforceBudget`: under budget no-op, over budget evicts, FIFO without store, score-based with store, file rewritten correctly, custom budget, multiple blank line cleanup
- `TestCategorizeIndex`: groups by type (semantic→Knowledge, episodic→Session History, procedural→Procedures), unknown type defaults to Knowledge, preserves title, file rewritten

### Key file
- `src/memoryschema/l0_budget.py` — 4 functions: `estimate_tokens`, `parse_index_entries`, `enforce_budget`, `categorize_index`

**Verification:** Tested (all functions exercised with assertions)

## Phase 2 — E2E pipeline test ✓ 665eb8a

No single test exercises write → gate → embed → store → recall. The closest is test_consolidation.py (discover → parse → upsert) but it skips the gate and recall.

### 2.1 Create tests/test_e2e_pipeline.py
- `TestWriteGateStoreRecall`:
  - `test_accept_store_recall` — memory dict → gate_pipeline ACCEPT → upsert → recall by query returns it (mocked embeddings)
  - `test_reject_never_stored` — nameless memory → REJECT → not in store
  - `test_quarantine_stored_with_status` — provenance conflict → QUARANTINE → stored with status=quarantined
- `TestRelationCascade`:
  - `test_backlink_recall` — create A, create B with INFORMS→A, compute_backlinks, recall A at depth=1, verify B appears via backlink channel

### Key files
- `src/memoryschema/write_gate.py` — `gate_pipeline(memory, store, config)`
- `src/memoryschema/store.py` — `MemoryStore.upsert()`, `MemoryStore.recall()`

**Verification:** Tested (full pipeline exercised end-to-end in one test)

## Phase 3 — Fix reflect clustering (0 clusters) ✓ 84edacf

`_cluster_by_associations` uses connected components via BFS. With k-NN associating all episodic entries transitively, they form one giant component (size ~17) that exceeds `max_cluster=10`. Result: 0 clusters output.

### 3.1 Add score threshold to _cluster_by_associations
- Add `score_threshold=0.7` parameter to `_cluster_by_associations(entries, min_cluster, max_cluster, score_threshold)`
- Filter adjacency edges: only add edge if `assoc.score >= score_threshold`
- This breaks the giant component into smaller clusters of highly related entries
- `reflect()` passes threshold through (default 0.7)
- CLI `--score-threshold` option (optional, can defer)

### 3.2 Add tests
- `test_threshold_splits_components` — 4 entries, 2 pairs with high-score (0.9) edges, cross-pair low-score (0.5). Threshold 0.7 → 2 clusters of 2.
- `test_threshold_zero_preserves_old_behavior` — threshold=0 gives connected components (old behavior)
- `test_single_giant_component_filtered` — reproduce the real bug: 10+ entries all connected, max_cluster=10, threshold=0.7 → smaller clusters

### Key file
- `src/memoryschema/consolidation.py` — `_cluster_by_associations()` (lines 92-128), `reflect()` (line 239)

**Verification:** Tested + Operative (reflect produces >0 clusters on fixture data)

## Phase 4 — Fix Neo4j auth + improved error handling ✓ b0fec82

docker-compose.yml uses `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}` (shell variable). Container started without NEO4J_PASSWORD set → auth undefined. Constructor has no error handling — raw Neo4j error bubbles up.

### 4.1 Fix Neo4j connection
- Set `NEO4J_PASSWORD=changeme` in environment
- Recreate container: `docker compose down && docker compose up -d`
- Wait for healthy, run `memoryschema neo4j schema`
- Migrate: `memoryschema migrate jsonl-to-neo4j`
- Verify: `memoryschema neo4j status` shows connected, 34 nodes

### 4.2 Add auth error handling to Neo4jMemoryStore.__init__
- Wrap the `session.run('RETURN 1')` connectivity check in try/except
- On auth error: raise `ConnectionError` with actionable message ("Set NEO4J_PASSWORD env var or check memoryschema.toml")
- Test: mock driver to raise auth error, verify ConnectionError with helpful message

### Key files
- `docker-compose.yml` — `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}`
- `src/memoryschema/neo4j_store.py` — `__init__` (lines 59-78)

**Verification:** Operative (neo4j status shows connected + 34 nodes)

## Phase 5 — Hook integration test (session 18 residual) ✓ 30e7a1b

The hook's Python block calls gate_pipeline with store + config. This was fixed in E2 but never verified end-to-end. Phase 0 fixes the parse-error path; this phase tests the gate pipeline path.

### 5.1 Add hook pipeline tests to tests/test_e2e_pipeline.py
- `TestHookPipeline`:
  - `test_gate_pipeline_with_store_and_config` — construct same objects as hook (MemoryStore, MemoryConfig), run gate_pipeline, verify ACCEPT
  - `test_quarantine_on_provenance_conflict` — seed first-party entry, gate_pipeline with ingested entry of same name → QUARANTINE
  - `test_memory_md_update_logic` — replicate hook's MEMORY.md update: append entry, enforce_budget, categorize_index, verify file correct
  - `test_neo4j_fallback_to_jsonl` — patch Neo4j import to raise ImportError, verify JSONL upsert succeeds

### Key file
- `src/memoryschema/hooks/hook-post-write.sh` — Python block (lines 38-175)

**Verification:** Tested (hook's Python logic exercised as callable with same construction)

## Phase 6 — Neo4j integration test (optional) ✓ b56090f

16 mocked tests verify logic but not real connectivity. A single integration test confirms the Phase 4 fix.

### 6.1 Add pytest integration marker
- Register `integration` marker in `pyproject.toml`
- Standard `pytest` run skips integration tests; `pytest -m integration` runs them

### 6.2 Add Neo4j integration test to tests/test_neo4j_store.py
- `TestNeo4jIntegration` (marked `@pytest.mark.integration`):
  - `test_connect_and_count` — connect to real Neo4j, verify count() returns integer
  - `test_upsert_get_roundtrip` — upsert test entry, get it back, verify fields, clean up
  - Skip guard: try/except on connection failure → pytest.skip

### Key file
- `tests/test_neo4j_store.py`

**Verification:** Operative (real container round-trip verified)

## Verification Criteria

| # | Criterion | Phase | Status type |
|---|-----------|-------|-------------|
| 0 | Auto-memory writes no longer produce hook parse errors | 0 | Operative |
| 1 | l0_budget.py has dedicated test coverage for all 4 functions | 1 | Tested |
| 2 | Single test exercises write → gate → store → recall | 2 | Tested |
| 3 | reflect() produces >0 clusters on fixture data | 3 | Tested |
| 4 | Neo4j status shows connected + 34 nodes | 4 | Operative |
| 5 | Hook Python block verified with same gate_pipeline args | 5 | Tested |
| 6 | Real Neo4j upsert/get round-trip passes | 6 | Operative |
