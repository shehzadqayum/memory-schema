---
schema: 5
importance: 7
relations:
  - USES plan-memory-schema-fix
  - MITIGATES memory-schema-known-bugs
---

memory-schema reliability fix COMPLETE (2026-06-30)…

## Summary

memory-schema reliability fix COMPLETE (2026-06-30): idempotent Neo4j schema + migrate, a comprehensive no-residual `reconcile`, an always-on `preflight` dependency gate, and loud (never silent) degradation — Voyage+Neo4j up is the verified default mode.

## Observations

- EquivalentSchemaRuleAlreadyExistsException ROOT CAUSE + FIX: schema.py create_schema used the legacy `CALL db.index.vector.createNodeIndex` (no IF NOT EXISTS); replaced with the modern `CREATE VECTOR INDEX memory_embedding IF NOT EXISTS FOR (m:Memory) ON (m.embedding) OPTIONS {indexConfig:{vector.dimensions:1024, vector.similarity_function:'cosine'}}` (Neo4j 5.11+ GA DDL). `neo4j schema`/`reset` now run repeatedly without throwing.
- Idempotent migrate: migration.py migrate_nodes changed from a bare CREATE to `MERGE (m:Memory {name}) SET m += props`, so `migrate jsonl-to-neo4j` is safe against existing nodes (no ConstraintError). Edits made while Neo4j is down no longer need a destructive reset+reimport to resync — re-running migrate (or reconcile) is enough. This RETIRES the step-132 lesson that jsonl-to-neo4j was not idempotent.
- Comprehensive sync: new `memoryschema reconcile` (reconcile.py) treats the .md files as content-truth, rewrites store.jsonl to EXACTLY the .md name-set (reusing the JSONL-derived embeddings when content is unchanged, else a full multi-space embed_all_spaces), idempotently pushes to Neo4j, prunes Neo4j orphans (post-import re-list), recomputes associations, and verifies by name-set. Heals drift in all three layers with NO residuals; a second run is a no-op. `sync` upgraded from a count-compare to a read-only name-set diff. Flags: --dry-run, --prune/--no-prune, --no-verify.
- Always-on dependency health: new `memoryschema preflight` (preflight.py) checks Docker engine, the helios-neo4j container (AUTO-STARTS it if stopped — but never launches Docker Desktop itself), bolt + the vector schema, and Voyage; prints a loud per-check report and exits non-zero when a hard-required dep is down. A throttled (60s `.preflight_ok` marker) banner-only auto-preflight runs on CLI entry. Config gained require_neo4j (default TRUE) and require_voyage (default FALSE).
- Loud, never-silent degradation: get_store() no longer swallows Neo4j failures (the old `except Exception: pass` is gone). With require_neo4j it RAISES ConnectionError; otherwise it prints a DEGRADED banner to stderr and falls back to the JSONL store so reads stay functional. The explicit `index` materialize command passes require_neo4j=config.require_neo4j so it fails loud (clean ClickException, non-zero exit) rather than silently writing JSONL-only drift; the hook + read paths intentionally STAY on graceful-degrade+banner so a routine memory Write never loses the .md content-truth (drift heals on the next reconcile).
- VERIFIED end-to-end (2026-06-30): the full hermetic suite is green (pytest exit 0; CI/doctor run with no live Neo4j). Live walk-through against the real helios-neo4j container — baseline preflight 5/5 green; Neo4j down then preflight FAIL (exit 1) + recall DEGRADED banner yet still returns via JSONL/BM25 + `index` hard-fails loud (exit 1); preflight then auto-RECOVERED the container to 5/5; reconcile 42/42/42 Verify PASS + an idempotent no-op rerun; live store integrity intact. 13 new tests across test_schema_idempotent / test_preflight / test_get_store_degrade / test_reconcile.
- Layering decision (canonical): the .md entities are CONTENT-truth; store.jsonl is the MATERIALIZED canonical (carries default + 7-space embeddings, divergence_profile, timestamps, associations); Neo4j is a REBUILDABLE projection of the JSONL. reconcile enforces this top-down (.md to JSONL to Neo4j). KNOWN follow-up: the suite is only hermetic when no live Neo4j is reachable, because conftest strips NEO4J_URI but MemoryConfig falls back to the localhost default — running pytest with the container UP connects to it (slow, non-mutating). All edits are to the VENDORED packages/memory-schema — re-apply on package re-vendor.

## Notes

memory-schema reliability hardening — see [[plan-memory-schema-fix]] for the approved plan. Resolves the EquivalentSchemaRuleAlreadyExistsException and the non-idempotent migrate flagged in [[memory-schema-known-bugs]]; complements [[memory-schema-bugs-fixed]] and the [[neo4j-upsert-null-observations-bug]] fix. Part of the [[chain-session-2026-06-21]] working chain.

Migrated from helios 2026-07-13 (extraction seeding).
