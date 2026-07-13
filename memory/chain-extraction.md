---
schema: 5
---

Repo born by extraction from helios; first-session setup notes recorded

## Summary

Repo born by extraction from helios; first-session setup notes recorded

## Log

- Step 1: Step recorded from the extraction session (run from the helios venv). This repo was born 2026-07-13 by git subtree split from helios (79 commits) + a seeded memory store (108 entities: 23 helios-era package-dev + 85 curated genesis, see the seed commit + memory-migration-manifest in helios). Remote: github.com/shehzadqayum/memory-schema (main; genesis branch = June history; deployments/helios = consumer state + ledger). FIRST-SESSION SETUP NEEDED HERE: (1) create .env with VOYAGE_API_KEY + NEO4J_PASSWORD; (2) either start this project's own Neo4j (memoryschema neo4j up -> container memory-schema-neo4j) or run JSONL-only (MEMORYSCHEMA_REQUIRE_NEO4J=false) - the store currently has JSONL+embeddings only, Neo4j pending; (3) a venv with pip install -e .[all] (this step ran from the helios venv); (4) memoryschema hook install if Claude sessions will write memories here. Known milestone triggers carried in the migrated memories: multi-space re-test + backend re-benchmark + numeric-probe re-check at the 250-entity corpus milestone; historical git-state replay deliberately deferred.
- Step 2: Package feedback from the fractal pip-path bootstrap (first real pip consumer, install from git+https@v0.1.0 - WORKED: site-packages artifacts deployed via init, per-project hooks registered from site-packages paths, compose parameterization gave fractal-neo4j on 7475/7688 from a TOML-first init). One rough edge found: `plugin sync --check` compares against ALL packaged artifacts while `init --scopes working` (the default) deliberately deploys only the working scope - so every fresh working-scope project reports phantom drift on rules-ondemand/memory-corpus.md until a full `plugin sync`. Fix candidate: record the chosen scopes (e.g. in memoryschema.toml [project] scopes=...) and have sync/--check respect them; or treat not-deployed corpus-scope files as in-scope-absent rather than missing. Also BOOTSTRAP.md was corrected (0db9af6): the old bare `pip install memory-schema[all]` was a dependency-confusion hazard (package is NOT on PyPI); now pinned git+https forms + warning; first tag v0.1.0 cut.
