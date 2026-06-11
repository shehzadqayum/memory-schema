# Full Documentation Alignment — Verification Audit + Gap Coverage

## Context

Post-session-11 verification audit plus deep gap analysis. Three agents audited every source file, doc surface, CLI flag, config field, and algorithm. Found: 1 remaining factual error, 41 undocumented features/behaviors, and weak coverage of critical features (trust guards in 1/10 surfaces, SUPERSEDES authority in 1/10). Plan fixes errors first, then expands existing docs for full coverage.

## Prior Residuals (from [S4] 4747602)

None.

## Phase 1: Fix remaining factual error (1 fix) ✓ 9942b0f

### 1A. hierarchy-and-inheritance.md:416 — "Schema stays v2" → "Schema stays v3"
Second occurrence missed in session 11. Line 10 already fixed.

## Phase 2: Expand technical-reference.md (missing CLI flags, config, scoring, audit) ✓ 9a31320

### 2A. CLI flags reference — add ALL undocumented options
After each command in the CLI table, add flags column. Missing flags:
- `recall/list/search --include-inactive`
- `validate --strict`
- `hook install --timeout, --per-project`
- `index --base-path, --project`
- `embed --batch-size, --coverage, --dry-run`
- `associations --k, --recompute`
- `backup --neo4j-only, --jsonl-only, --files-only`
- `reset --neo4j-only, --store-only, --working-memory-only`
- `clean --dry-run`
- `export --format, --output`
- `import --format`
- `doctor --fix`
- `init --neo4j-password`
- `migrate jsonl-to-neo4j --batch-size, --skip-assoc`

### 2B. Scoring algorithm detail section
Expand the existing scoring section to document:
- BM25 parameters (k1=1.2, b=0.75, avg_dl=50, normalized to 0-0.3)
- Weight redistribution when no embedding (40% recency, 60% importance)
- Neo4j vs JSONL text match divergence
- Numpy vectorized path (graceful fallback to pure Python)

### 2C. Audit trail format
Add new section documenting audit.jsonl schema:
- `gate_decision` records: timestamp, operation, name, verdict, reasons, provenance
- `mutation` records: timestamp, operation, name, changes (field-level hashes), prior hashes
- Append-only, never truncated

### 2D. Graceful degradation detail
Add section documenting:
- Neo4j down: silent fallback to JSONL (get_store tries Neo4j, catches all exceptions)
- Voyage AI missing: entries indexed without embeddings, warning logged
- Embedding failure: non-blocking, entry saved unembedded
- Concurrent writes: fcntl advisory locking (Unix), no-op fallback (Windows)
- Audit failure: silently swallowed, never blocks mutations

## Phase 3: Expand schema.md behavioral spec (trust, L0, reflect) ✓ fd258c3

### 3A. Trust multiplier detail
Expand §Provenance Semantics to include:
- Trust level hierarchy table: user=3, first-party=3, derived=3, ingested=1
- Why derived=3: consolidation (reflect) creates derived summaries that supersede episodic entries
- Scoring impact example: ingested entry scores 30% lower than first-party

### 3B. L0 budget enforcement detail
Expand §MEMORY.md Index to document:
- Token estimation: chars/4 approximation
- Eviction: score-based (lowest-scoring first), FIFO fallback when no store
- Progressive disclosure: categorize_index groups entries by type (Knowledge, Procedures, Session History)
- Token budget default: 2000 tokens (configurable via l0_token_budget)

### 3C. Reflect/consolidation algorithm
Expand §Behavioral Specification "On Consolidate" to document:
- Clustering: adjacency graph from associations, BFS connected components, min/max cluster size filtering
- Synthesis: tries LLM via Anthropic SDK, falls back to mechanical merge (concatenate descriptions, dedup observations)
- Output: creates SUPERSEDES edges from summary to cluster members, importance = max of cluster

### 3D. Project auto-derivation
Add to §Entity Structure or hierarchy doc:
- tags.py derives project from filepath: looks for `projects/<name>/` segments
- Supports nested: `projects/parent/projects/child/` → `parent.child`
- Strict kebab-case validation for segments

## Phase 4: Expand README.md (operational completeness) ✓ 5f7c8b3

### 4A. Hook behavior detail
Expand the hook section (lines 99-105) to document the full pipeline:
1. Fires on every Write to `memory/*.md`
2. Parses `<memory:entity>` XML
3. **Runs write gate pipeline** (REJECT/QUARANTINE/ACCEPT)
4. Embeds via Voyage AI (if key set, non-blocking on failure)
5. Indexes to Neo4j (primary) or JSONL (fallback)
6. **L0 gating: ingested entries never enter MEMORY.md**
7. Appends to MEMORY.md (compact resilience)
8. **L0 budget enforcement** (evicts lowest-scoring if over token limit)

### 4B. Graceful degradation table
Expand the troubleshooting/degradation section with a clear table:
| Component | If missing | Behavior | Fix |
|-----------|-----------|----------|-----|
| Neo4j | JSONL fallback | Silent, automatic | Install Docker + deploy |
| Voyage AI | No embeddings | Keyword search only | Set VOYAGE_API_KEY |
| Docker | No Neo4j | JSONL only | Install Docker |
| Claude Code | No auto-indexing | Manual `write` | Install hook |
| Hook | No auto-indexing | Manual `write` command | `memoryschema hook install` |

## Status: COMPLETE

All 4 phases delivered. 11/11 audit items PASS. Zero residuals. 472 tests passing.

## Verification

1. `python -m pytest tests/ -v` — 472 pass
2. `grep -rn "stays v2" docs/hierarchy-and-inheritance.md` — zero matches
3. `memoryschema --help` — all commands listed
4. `diff src/memoryschema/templates/memory-schema.rules.tpl .claude/rules/memory-schema.md` — identical
5. Coverage matrix: trust multiplier documented in ≥3 surfaces, SUPERSEDES guards in ≥2

## Out of Scope (historical records)

- 21 memory files with schema="2" — historical working memories, backward compatible, not user-facing
- Session reports 8-9 with stale counts — historical records, accurate at time of writing
- PKG-INFO build artifact — regenerated on next `pip install -e .`
