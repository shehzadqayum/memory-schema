# Full Documentation Alignment — Post-v3 Semantics

## Context

After the v3 semantics implementation (session 10, 8 phases), three comprehensive file-by-file audits found implementation bugs, security issues, stale examples, and 24 documentation gaps. This plan fixes implementation first, audits the result, then aligns all documentation to the verified implementation.

## Prior Residuals (from [S4] 1fb9276)

None.

## Phase 1: Implementation Fixes (code, security, examples, templates)

Fix all code-level issues before touching documentation. Tests must pass after each fix.

### 1A. Neo4j hub bonus formula divergence — SCORING BUG
`src/memoryschema/neo4j_store.py:681` — uses `0.05 * min(backlinks, 5)` (old linear, capped).
`src/memoryschema/store.py:665` — uses `0.05 * math.log(1 + backlinks)` (correct logarithmic).
**Fix:** Change neo4j to `0.05 * math.log(1 + backlinks)`, add `import math` if missing.
**Impact:** Scoring parity between backends. Hub-heavy entries scored differently until fixed.

### 1B. Docker-compose password — SECURITY
`docker-compose.yml:9` — hardcoded `NEO4J_AUTH=neo4j/changeme`.
`docker-compose.yml:18` — healthcheck uses `"-p", "changeme"`.
**Fix:** Use env var reference: `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}` and `"-p", "${NEO4J_PASSWORD}"`.
**Impact:** Known-bad password committed to repo.

### 1C. Validator R6 dead code — CODE CLEANUP
`src/memoryschema/validator.py:224` — `level = 'R6' if strict else 'R6'` always produces 'R6'.
**Fix:** Replace with `level = 'R6'`.

### 1D. Example scripts stale schema version — CODE
`src/memoryschema/examples/ingest_tweets.py:133` — schema="2"
`src/memoryschema/examples/ingest_forum.py:153` — schema="2"
`src/memoryschema/examples/consolidate_working.py:121` — schema="2"
**Fix:** All → schema="3".

### 1E. Examples README stale API — CODE
`src/memoryschema/examples/README.md:52` — `'schema': 2` → `'schema': 3`

### 1F. TOML template missing retrieval config
`src/memoryschema/templates/memoryschema.toml.tpl` — missing `l0_token_budget` and `max_inherit_depth`.
**Fix:** Add commented `# l0_token_budget = 2000` and `# max_inherit_depth = 3` to [retrieval] section.

## Phase 2: Implementation Audit

Verify the implementation is clean before documenting it.

### 2A. Full test suite
`python -m pytest tests/ -v` — expect 472 pass.

### 2B. Backend scoring parity check
Verify store.py and neo4j_store.py _score_entry produce same results for identical inputs:
- Hub bonus: both logarithmic
- Type factor: both have semantic/episodic/procedural modifiers
- Trust multiplier: both have provenance-based multipliers
- Weight redistribution: both handle missing embeddings

### 2C. Stale reference sweep
```
grep -rn 'schema="2"' src/ docs/ .claude/ README.md   # only test fixtures
grep -rn "changeme" .                                   # only memory/ historical
grep -rn "20-point\|20 components\|out of 20" src/ docs/
grep -rn "V1-V10\|R1-R5" src/ docs/ .claude/
grep -rn "min(backlinks" src/                            # should be 0 after 1A
```

### 2D. Template sync
`diff src/memoryschema/templates/memory-schema.rules.tpl .claude/rules/memory-schema.md` — must be identical before and after Phase 3.

## Phase 3: Documentation Alignment (24 fixes across 14 files)

All docs updated to match the verified implementation from Phase 2.

### Group A: Doctor check count (20 → 21) — 3 fixes
**3A.** `src/memoryschema/cli/doctor_cmd.py:318` — "Run 20-point" → "Run 21-point"
**3B.** `docs/implementation-guide.md:138` — "Checks 20 components" → "Checks 21 components"
**3C.** `docs/hierarchy-and-inheritance.md:328` — "out of 20 total" → "out of 21 total"

### Group B: Validation rule coverage — 5 fixes
**3D.** `.claude/rules/memory-schema.md:158` — "V1-V10 (structure), R1-R5 (relations)" → "V1-V13 (structure), R1-R7 (relations)"
**3E.** `src/memoryschema/templates/memory-schema.rules.tpl:158` — same (keep in sync)
**3F.** `src/memoryschema/cli/validate_cmd.py:14` — "V1-V10, R1-R5, F1-F3" → "V1-V13, R1-R7, F1, F3"
**3G.** `src/memoryschema/validator.py:10` — "Q1-Q7" → "Q1-Q2, Q6-Q8"
**3H.** `src/memoryschema/validator.py:63` — add Q8 to quality check list in function docstring

### Group C: schema.md validation table — 2 fixes
**3I.** `docs/schema.md:239` — Add V13: `| V13 | If provenance="ingested", must have <memory:source> element |`
**3J.** `docs/schema.md:249` — Add R7: `| R7 | No SUPERSEDES cycles (A→B→...→A chains rejected) |`

### Group D: Scoring formulas — 3 fixes
**3K.** `.claude/rules/memory-schema.md:139` + template — hub: "min(backlinks, 5)" → "ln(1 + backlinks)"; text match: "+0.1" → "+0.1 substring (Neo4j) or BM25 up to +0.3 (JSONL)"
**3L.** `docs/technical-reference.md:77-78` — same hub and text match formula fixes
**3M.** `docs/schema.md:281-282` — same text match update

### Group E: Rules file type factor + upsert — 4 fixes (rules + template)
**3N.** `.claude/rules/memory-schema.md` Rule 7 + template — add type factor: "semantic floor 0.6, episodic standard, procedural `recency^(1/(1+0.3*min(accesses,10)))`"
**3O.** `.claude/rules/memory-schema.md` Rule 6 + template — add: provenance (Immutable), status (Server-managed), project (Immutable)

### Group F: Missing CLI commands — 3 fixes
**3P.** `README.md` — add 6 commands: eval, reflect, archive, unarchive, reactivate, quarantine
**3Q.** `README.md` — hook subcommands: add uninstall, test
**3R.** `src/memoryschema/cli/main.py` docstring — add eval under "Validation & Quality"

### Group G: Schema version + module docstrings — 4 fixes
**3S.** `docs/hierarchy-and-inheritance.md:10` — "Schema stays at v2" → "Schema is v3."
**3T.** `src/memoryschema/store.py:1-13` — add v3 capabilities to docstring
**3U.** `src/memoryschema/tags.py:1-8` — add status/provenance parsing to docstring
**3V.** `src/memoryschema/__init__.py:1-27` — update API listing (reflect, hierarchy, inheritance)

### Group H: technical-reference.md completeness — 2 fixes
**3W.** `docs/technical-reference.md:138` — validator module "R1-R6" → "R1-R7"
**3X.** `docs/technical-reference.md` Configuration table — expand from 9 to ~16 fields (add: store_path, neo4j container/port fields, rerank_model, recall_depth, recall_decay, l0_token_budget, max_inherit_depth)

## Verification

1. `python -m pytest tests/ -v` — 472+ pass
2. `diff src/memoryschema/templates/memory-schema.rules.tpl .claude/rules/memory-schema.md` — identical
3. `grep -rn "20-point\|20 components\|out of 20\|V1-V10\|R1-R5\|Q1-Q7\|min(backlinks\|stays at v2" src/ docs/ .claude/ README.md` — zero matches
4. `grep -rn 'schema="2"' src/ docs/ .claude/ README.md` — only test fixtures
5. `grep -rn "changeme" docker-compose.yml` — zero matches
6. `memoryschema --help` — eval listed
7. `memoryschema doctor --help` — 21-point
8. `memoryschema validate --help` — V1-V13, R1-R7
