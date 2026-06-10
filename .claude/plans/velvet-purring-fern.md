# v3 Semantics + Precedence Fix + Docs Reconciliation

## Context

Re-audit after v3 structural work found: (1) config precedence code is correct (CLI applied last) but docs contradict each other across 4 files and examples show env winning; (2) status/provenance have validation but zero retrieval semantics — no filtering, no trust multiplier, no SUPERSEDES propagation, no write-gate operational spec; (3) documentation drift recurred — counts, formulas, schema versions still forked; (4) new issues from v3 changes — backend-divergent max_depth, secrets in TOML, $project_prefix undefined in filter Cypher.

## Prior Residuals (from [S4] 24870f9)

None.

## Phases

### Phase 1: Precedence fix + test ✓ 26b0f7e
- Add test: CLI > env > TOML (set all three, assert CLI wins)
- Reconcile all 4 docs to CLI-first ordering
- Fix hierarchy-and-inheritance.md Example 4 (env beats CLI → CLI beats env)

### Phase 2: Status lifecycle semantics ✓ a73ac09
- Implement retrieval filtering: exclude non-active from recall/search/list (opt-in flags)
- Superseded: traversable-not-returned in cascade BFS
- SUPERSEDES propagation with trust + authority guards
- Cycle detection (R7)
- Archive/unarchive/reactivate commands
- Quarantine review commands (list/release/reject)
- MEMORY.md line removal on status transition
- Document all transitions + consequences in schema.md

### Phase 3: Provenance trust semantics ✓ 19fb8ec
- Provenance immutability in upsert (join name/project in merge exclusion)
- Trust multiplier on final score (configurable: user=1.0, first-party=1.0, derived=0.9, ingested=0.7)
- L0 invariant: MEMORY.md excludes ingested (stated as rule, not append-path accident)
- Ingested presentation: untrusted-data delimiters in recall output
- Source-required-if-ingested gate rule
- Document in schema.md

### Phase 4: Write gate operational spec ✓ e0de311
- Reject (structural) vs quarantine (suspicion) — two-verdict pipeline
- Gate pipeline: validation → provenance admission → guards → consistency probe → commit
- Quarantine storage: markdown + JSONL, unembedded, reviewable
- CLI: memoryschema quarantine list/review/release/reject
- Audit log: machine-readable verdict + reason
- Never silently drop
- Document pipeline in schema.md Behavioral Specification

### Phase 5: Type factor implementation ✓ 5d7811d
- semantic: effective_recency = max(recency, 0.6)
- episodic: effective_recency = recency (standard)
- procedural: recency^(1/(1 + 0.3*min(access_count, 10)))
- Wire into _score_entry() in both store.py and neo4j_store.py
- Document in schema.md scoring section

### Phase 6: Behavioral specification additions ✓ cc95b5c
- On Supersede, On Archive, On Delete, On Quarantine, On Mutate entries
- Delete: remove md + JSONL + Neo4j + MEMORY.md + inbound edges (audit-logged)
- Upsert table: add status (server-managed), provenance (immutable)

### Phase 7: Documentation reconciliation ✓ 4201b24
- Fix all count forks (432 tests / 21 doctor / 28 files everywhere)
- Fix all category table sums
- Fix schema="3" in all examples
- Fix R2 wording ("six active types, two deprecated")
- Remove stale references (scripts/memory-server/, ict-neo4j)
- tech-ref: update from v2 to v3, add status/provenance, fix scoring formula
- impl-guide: remove contradictory "every response" sentence
- system-overview: update optional field count (10 not 8)
- Add v3 row to schema versioning table

### Phase 8: Small holes ✓ 211663d
- Neo4j max_depth: post-filter on results (or reject with error)
- $project_prefix dot-boundary: ensure + '.' in filter-mode Cypher
- Secrets: remove api_key/password from TOML examples, document env-only
- Randomised Neo4j password: reflect in config table (remove changeme default)
- eval + reflect + archive in CLI reference tables

## Status: COMPLETE

All 8 phases delivered. 472 tests passing. 10/10 verification criteria PASS (1 deferred: live doctor).

## Verification

1. Test: CLI > env > TOML (all three set, CLI wins)
2. Test: recall excludes superseded/archived by default, includes with opt-in
3. Test: SUPERSEDES sets target status, trust guard blocks ingested→first-party
4. Test: provenance immutable on upsert
5. Test: type factor modifies recency correctly
6. Test: quarantine stores unembedded, release embeds
7. All counts consistent across docs (432/21/28)
8. No schema="2" in any example
9. python -m pytest tests/ -v — all pass
10. memoryschema doctor — all pass
