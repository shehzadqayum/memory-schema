---
schema: 5
---

Repo born by extraction from helios; first-session setup notes recorded

## Summary

Repo born by extraction from helios; first-session setup notes recorded

## Log

- Step 1: Step recorded from the extraction session (run from the helios venv). This repo was born 2026-07-13 by git subtree split from helios (79 commits) + a seeded memory store (108 entities: 23 helios-era package-dev + 85 curated genesis, see the seed commit + memory-migration-manifest in helios). Remote: github.com/shehzadqayum/memory-schema (main; genesis branch = June history; deployments/helios = consumer state + ledger). FIRST-SESSION SETUP NEEDED HERE: (1) create .env with VOYAGE_API_KEY + NEO4J_PASSWORD; (2) either start this project's own Neo4j (memoryschema neo4j up -> container memory-schema-neo4j) or run JSONL-only (MEMORYSCHEMA_REQUIRE_NEO4J=false) - the store currently has JSONL+embeddings only, Neo4j pending; (3) a venv with pip install -e .[all] (this step ran from the helios venv); (4) memoryschema hook install if Claude sessions will write memories here. Known milestone triggers carried in the migrated memories: multi-space re-test + backend re-benchmark + numeric-probe re-check at the 250-entity corpus milestone; historical git-state replay deliberately deferred.
