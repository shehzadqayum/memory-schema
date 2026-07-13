---
schema: 5
importance: 8
status: superseded
superseded_at: 2026-07-04
superseded_by: memory-schema-reliability-hardened
relations:
  - USES seven-space-scoring-activated
  - USES neo4j-upsert-null-observations-bug
---

APPROVED plan + decisions (2026-06-30) to fix the vendored memory-schema…

## Summary

APPROVED plan + decisions (2026-06-30) to fix the vendored memory-schema: idempotent schema, correct reconcile w/ orphan-prune, always-on dependency health (loud not silent), e2e tests. Executing P0-P6.

## Observations

- ROOT CAUSES (all confirmed at file:line in packages/memory-schema/src/memoryschema): (1) schema.py:31 creates the vector index via legacy db.index.vector.createNodeIndex(...) with NO 'IF NOT EXISTS' (siblings at :26/:41/:47 have it) -> EquivalentSchemaRuleAlreadyExistsException on 2nd run, breaks reset/schema/deploy. (2) migration.py:69 does a bare CREATE -> ConstraintError vs existing nodes; migrate_cmd.py:95-129 'sync' only count-compares (never upserts/prunes) -> only working resync is a destructive wipe + orphans never removed. (3) store.py:1103-1112 get_store() swallows every Neo4j failure (except Exception: pass), discarding the typed ConnectionError -> writes land JSONL-only, drift accrues silently; deps only checked on-demand via slow doctor. (4) tests don't cover any of it (schema test mock swallows the exception; fallback test never asserts a warning).
- FIX 1 (P0, schema idempotency): container is Neo4j 5.26.27 (modern DDL GA since 5.11). Replace schema.py:30-38 with `CREATE VECTOR INDEX memory_embedding IF NOT EXISTS FOR (m:Memory) ON (m.embedding) OPTIONS {indexConfig:{`vector.dimensions`:1024,`vector.similarity_function`:'cosine'}}` (backticks on dotted keys required). Makes reset/schema/deploy re-runnable. The db.index.vector.queryNodes call-sites in neo4j_store.py are the QUERY proc — unchanged. Only m.embedding is index-backed; the 6 multispace vectors are Python-scored.
- FIX 2 (idempotent reconcile, no residuals): canonical layering = .md is CONTENT truth, store.jsonl is the derived-layer cache (embedding/embeddings/divergence_profile/associations/backlinks/created_at/access_count), Neo4j is a rebuildable projection. F1 (P1): migration.py:67-71 CREATE -> `MERGE (m:Memory {name}) SET m += nd.props` (the proven path at neo4j_store.py:177-199). F2 (P2): new `memoryschema reconcile [--from md|jsonl] [--dry-run] [--prune] [--verify]` — build canonical from .md with per-entity content HASH, reuse JSONL derived layer where unchanged (re-embed only new/changed), MERGE-upsert into Neo4j, DETACH DELETE orphans (the no-residuals step), recompute associations, VERIFY by name-set+sampled-hash (not counts); 2nd run = no-op. F3: upgrade stub `sync` to a read-only drift diagnostic. F4 (P5): hook drops memory/.neo4j_dirty on the down-branch + auto-replays on next reachable write.
- FIX 3 (dependency health at all times = default mode): new preflight.py:ensure_backend() — fast, distinct from doctor: Docker engine -> container (auto `neo4j up` if merely stopped; NEVER auto-start Docker Desktop) -> bolt -> schema -> Voyage embed. Wired at 3 points (P3/P4): throttled preflight in main.cli() (60s cache via memory/.preflight_ok), DE-SILENCE get_store() (loud DEGRADED banner + RAISE when require_neo4j), and the hook down-branch. New MemoryConfig.require_neo4j=True / require_voyage=False. POLICY (operator-confirmed defaults): writes HARD-REQUIRE Neo4j (JSONL-only writes cause drift); reads warn-loud but proceed; Voyage warn+degrade to BM25; Docker daemon down = FAIL LOUD + instruct; container stopped = AUTO-RECOVER via neo4j up.
- FIX 4 (e2e tests): respect the hermetic conftest.py (_isolate_from_live_backend strips live creds for unit tests; integration tests are prefix-scoped + try/finally + skip-if-down; NO live reset). Append any new env var (MEMORYSCHEMA_REQUIRE_NEO4J) to _LIVE_BACKEND_ENV. New/extended: test_schema_idempotent (create_schema twice, no throw), test_reconcile (drift->reconcile->exact match + 0 residual orphans + no-op rerun, unit plan + gated integration), test_cli_migrate (re-run migrate no ConstraintError; sync reports orphans), test_preflight (all-up ok; neo4j-down -> non-zero exit + visible DEGRADED on stderr = the anti-silent guarantee; voyage-down graceful), extend test_e2e_pipeline (assert the fallback WARNING).
- PHASES (memory module = high priority, ordered): P0 schema IF NOT EXISTS (S) -> P1 idempotent migrate MERGE (S) -> P2 reconcile command + real sync (L) -> P3 preflight.py + config (M) -> P4 wire preflight into CLI/get_store/hook + de-silence (M) -> P5 hook .neo4j_dirty self-heal (S) -> P6 full test suite (M). Operator decisions CONFIRMED: auto-start container yes / Docker Desktop no; writes hard-require + reads warn; require_voyage=False; .md is content-truth. CAVEAT: all edits land in the VENDORED packages/memory-schema — add to the local-patch list, re-apply on re-vendor; `memoryschema hook upgrade` overwrites hook-post-write.sh so the hook patches (backslash-path, .env autoload, + the new DEGRADED/self-heal) must be re-applied after any hook upgrade.

## Reasoning

These four defects share one theme: the system treated Neo4j+Voyage as optional (silent fallback) when the operator's default mode is that they are ALWAYS up and verified. The fix makes that invariant code-enforced (require_neo4j, loud degradation, preflight) and makes the recovery path correct (idempotent schema + an idempotent reconcile that prunes orphans, so a drift after downtime heals completely without residuals). Baseline: the existing ~735-test suite is green but covers NONE of these modes — hence Fix 4. Supersedes the ad-hoc resync we did manually (reset+reimport) with a proper reconcile command.

## Chain

chain-session-2026-06-21

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
