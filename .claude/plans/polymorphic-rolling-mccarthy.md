# Memory System v3 — Remediation & Research Alignment — Status: PROPOSED

## Context

A full audit of the system (schema.md, system-overview.md, technical-reference.md, implementation-guide.md, three completed plans) identified 28 issues across six categories: documentation drift, unimplemented semantics, scoring defects, hierarchy bugs, security/trust gaps, and absent evaluation. The dominant findings:

1. **Lifecycle is incomplete** — no delete/archive, SUPERSEDES unconsumed, MEMORY.md overflow unspecified.
2. **Trust is absent** — no provenance model, no write gate, L0 auto-load is an unconditional injection channel. Current research (MINJA, AgentPoison, MemoryGraft; arXiv 2604.16548 survey) identifies similarity-only retrieval without provenance as the canonical memory-poisoning precondition.
3. **Scoring is unvalidated** — importance encodes scope rather than salience, type system is inert, weights are untested hyperparameters, reranker unused.
4. **Docs have forked** — schema.md no longer describes actual scoring; counts disagree across four documents.

## Prior Residuals (from [S4] 3aa0777)

- R1: Neo4j max_depth not honored → addressing in Phase 4.6 (set finite default via TOML `retrieval.max_inherit_depth`)

Research anchors: Anthropic memory tool + context editing (agent-curated CRUD, 39% multi-step gain, 84% token reduction); Anthropic "Effective context engineering" (selective curation, progressive disclosure, just-in-time retrieval); Anthropic Managed Agents memory (per-write audit logs, scope/freshness/conflict/trust as the core questions); memory-security literature (pre-consolidation validation as privileged state transition).

## Validated Claims (verified against codebase)

| Claim | Status | Evidence |
|-------|--------|----------|
| SUPERSEDES not consumed | Confirmed | store.py:133-143 — no special handling; recall doesn't filter |
| CONTRADICTS not symmetric | Confirmed | store.py:133-143 — directed edge only, no reverse |
| Delete doesn't clean MEMORY.md | Confirmed | hook appends only, delete has no MEMORY.md cleanup |
| Reranker defined but unused | Confirmed | embeddings.py:84-116 exists, never called in recall |
| MEMORY.md grows unbounded | Confirmed | No token budget, no eviction, append-only |
| Sibling prefix correctly guarded | Confirmed | hierarchy.py:70 — `+ '.'` boundary prevents false matches |
| Consolidation is batch indexing only | Confirmed | consolidation.py:75-81 — no clustering/reflection |
| Hook installs globally | Confirmed | hook_cmd.py:12-14 — `~/.claude/settings.json` |
| No audit logging | Confirmed | No mutation logging anywhere in codebase |
| last_accessed correct | Confirmed | Updated on upsert/access only, not during scoring |

## Approach

Six phases, ordered by dependency: reconcile documentation first (cheap, unblocks everything), then lifecycle semantics, then trust/provenance (requires lifecycle's status field), then hierarchy hardening, then retrieval quality, then evaluation. Schema bumps to v3 (two new optional fields, one new server-managed field). Fully backward compatible — v1/v2 files remain valid.

---

## Phase 0: Documentation Reconciliation ✓ 1fa9148

**Problem:** schema.md claims authority but technical-reference.md alone documents the hub bonus and text-match boost; R2 says six relation types against a table of eight; test counts span 262-390 across docs; doctor counts span 18-20.

**Fixes:**
- Move the complete scoring formula (per-query-type weights, hub bonus, text-match boost, fallback redistribution) into schema.md Retrieval Scoring. technical-reference.md references it, never restates it.
- R2: "one of the eight defined types" (or better — see Phase 4, reduce to seven).
- Single generated constants block: test count, doctor check count, module list emitted by a `make docs-sync` script from the live codebase into all four documents. Doc drift becomes a CI failure, not a review finding.
- implementation-guide.md: regenerate test/doctor figures; document that `hook install` writes to the **global** `~/.claude/settings.json` and what that means for multi-project machines (or move to per-project `.claude/settings.json` — preferred, see Phase 3).

**Files:** `docs/schema.md`, `docs/technical-reference.md`, `scripts/docs_sync.py` (new), CI config.

---

## Phase 1: Lifecycle Completion

### 1.1 Status field (schema v3) ✓ 8b9411e
Add optional attribute `status`: `active` (default) | `superseded` | `archived` | `quarantined`. Server may set it (supersession propagation); author may set `archived`.

### 1.2 SUPERSEDES consumption ✓ e5e7757
- On upsert of a memory with `SUPERSEDES -> X`: server sets X's `status=superseded`.
- Retrieval: superseded entries excluded from default recall; included only with `--include-superseded`. Score multiplier 0.0 default, configurable.
- `CONTRADICTS`: enforce symmetry at upsert (write the reverse edge); recall surfaces both sides with a conflict marker rather than silently ranking one.

### 1.3 Delete/archive operations ✓ e35ac2d
- `memoryschema archive <name>` / `memoryschema delete <name>` — delete removes markdown + JSONL line + Neo4j node + MEMORY.md line, and **rewrites inbound relations** (flag dangling targets).
- Behavioral Specification gains **On Archive** and **On Delete** entries.
- Add referential-integrity validation rule **R6: relation targets must resolve to existing memories** (warning in standard mode, error in strict).

### 1.4 MEMORY.md budget and eviction ✓ 13cf5cc
- Replace "stays under 200 lines" with an explicit token budget (configurable, default ~2,000 tokens) enforced by the hook.
- Eviction on overflow: lowest `retrieval_score` lines are dropped from L0 (the entity persists in L1+; only index visibility changes). Log evictions.
- Aligns L0 with Anthropic context-editing findings: budgeted, curated context outperforms unconditional accumulation.

### 1.5 Consolidation as reflection, not just indexing ✓ 94b43d6
Extend `consolidation.py`: periodic job that (a) clusters episodic entries by association neighbourhood, (b) prompts a model to synthesise each cluster into one semantic summary entity with `SUPERSEDES` edges to members, (c) archives the members. This implements the documented episodic-to-semantic intent and is the standard reflection pattern in the agent-memory literature.

**Files:** `tags.py`, `validator.py`, `store.py`, `neo4j_store.py`, `consolidation.py`, `cli/memory_cmd.py` (archive/delete), hook script, `docs/schema.md` (v3 section).

---

## Phase 2: Scoring Integrity

### 2.1 Decouple importance from scope ✓ a01d126
- Remove the mandated 8-10/4-7 bands. Guidelines instead define scope via the `project`/scope mechanism (which already exists) and let importance mean salience.
- Replace "every response MUST write memory" with a selective-write rule: write when (a) a decision was made, (b) a correction was received, (c) novel durable fact established. This matches Anthropic's curation guidance and stops importance-10 flooding.

### 2.2 Implement or remove type semantics ✓ 3db1da8
Implement (preferred): add a type term —
```
type_factor: semantic = 1.0 (no decay on recency term)
             episodic  = standard decay
             procedural = decay * (1 - min(access_count,10)/20)  # access reinforcement
```
Update schema.md to describe actual behaviour; delete the "design intent, not current implementation" caveat.

### 2.3 Dampening ✓ 57c3cc8
- Hub bonus: cap retained, but switch to log scale (`0.05 * ln(1+backlinks)`) to slow rich-get-richer compounding.
- `last_accessed` update: only refresh when the memory is actually returned to the agent (top-k), not for every candidate scored.

### 2.4 Specify embedding input ✓ 63962ec
Schema.md must state exactly what is embedded: recommend `name + description + observations + reasoning` truncated to model limit; body excluded (or chunked separately if corpus). Add a soft length ceiling on `reasoning` (strict-mode check).

**Files:** `store.py`, `neo4j_store.py`, `embeddings.py`, `.claude/rules/memory-working.md`, `docs/schema.md`.

**Note:** weight changes land **after** Phase 6's eval harness exists — tuning without measurement repeats the current defect.

---

## Phase 3: Trust, Provenance, and Write-Path Security

### 3.1 Provenance field (schema v3) ✓ 4ab8504
New optional attribute `provenance`: `first-party` (agent reasoning) | `user` (direct user statement) | `ingested` (external content) | `derived` (consolidation output). Default for hook-written working memory: `first-party`. Corpus ingest scripts must set `ingested`.

### 3.2 Trust-weighted retrieval and L0 gating ✓ 5707e15
- Retrieval multiplier per provenance class (configurable; `ingested` < 1.0 by default).
- **`ingested` entries never enter MEMORY.md.** L0 is reserved for first-party/user/derived content. This closes the unconditional-injection channel: corpus content is reachable only via explicit retrieval, where it arrives as quoted data, not ambient context.
- Recall output wraps `ingested` content in a delimiter marking it untrusted data (instruction/data separation at the retrieval boundary).

### 3.3 Pre-consolidation write gate ✓ d622367
Hook pipeline gains a validation stage before indexing: schema validity (existing) + provenance present + name-collision policy + (strict mode) consistency probe — if the new entry's embedding is near an existing entry with a contradictory description, flag for review rather than silently upserting. Treat every write as a privileged state transition (per the security survey's defensive corollary).

### 3.4 Audit log ✓ 87925aa
Append-only `memory/audit.jsonl`: one line per mutation (create/upsert/archive/delete/status-change) with timestamp, fields changed, prior `reasoning`/`body` hash (or full prior value for working memory). Mirrors Managed Agents' per-write audit trail; also fixes the silent destructive-replace in upsert.

### 3.5 Hygiene ✓ 03229db
- Hook scope: install to per-project `.claude/settings.json`, not global.
- `<memory:prompt>`: add a redaction pass option (configurable regex set) and a documented retention statement; note Voyage egress in docs.
- Kill the `changeme` documented default — `memoryschema init` generates a random Neo4j password into `.env`.
- Rules attestation (lightweight): `doctor` records a hash of the effective parent rule set; changes surface as a check delta, so silent parent-side rewrites of child behaviour become visible in both directions.

**Files:** hook script, `store.py`, `neo4j_store.py`, `cli/doctor_cmd.py`, ingest scripts, `templates/`, `docs/schema.md`.

---

## Phase 4: Hierarchy Hardening

### 4.1 Single source of hierarchy ✓ f0502aa
Drop `PARENT_OF`/`CHILD_OF` as author-writable relation types (deprecate in v3; accept on read). Hierarchy is the dot-notation `project` field — period. If graph edges are wanted for Cypher traversal, the server **derives** them from project paths at index time. Eliminates the dual-source divergence and the redundant inverse pair (backlinks already give reverse traversal).

### 4.2 Dot-boundary prefix matching ✓ 4d89486
All Neo4j scope filters: `project = $p OR project STARTS WITH $p + '.'`. Add explicit sibling-prefix regression tests (`org` must not match `org-other`). Same boundary check in `hierarchy.py` string ops (verify — likely correct there, but test it).

### 4.3 Over-fetch widening ✓ e432914
`_vector_search`: if post-filter yields < k, iteratively widen (3x -> 9x -> full scan fallback) rather than returning a short list.

### 4.4 Precedence repair ✓ 68853ee
New order: **CLI flags > env vars > parent TOML > child TOML > defaults.** Rationale: explicit beats ambient; and parental enforcement should not be defeatable by `export`. If genuine env-based deployment overrides are needed, support an explicit `MEMORYSCHEMA_FORCE_*` prefix that ranks above CLI — opt-in, auditable.

### 4.5 Concurrency ✓ 34eb41b
JSONL store: advisory file lock (`fcntl`/`msvcrt`) around read-modify-write; document Neo4j as the recommended backend for concurrent parent/child sessions. Add a doctor check warning when multiple lock contentions are detected.

### 4.6 `max_depth` default ✓ a3fe9c5
Set a finite default (e.g. 3) for `project_matches_scope` in deep hierarchies via TOML (`retrieval.max_inherit_depth`), keeping `None` available. Unbounded read-up across an entire organisational tree is the memory analogue of a wildcard ACL.

**Files:** `hierarchy.py`, `neo4j_store.py`, `store.py`, `inheritance.py`, `config.py`, tests.

---

## Phase 5: Retrieval Quality

### 5.1 Rerank stage ✓ 695dde4
Recall path: cascade produces candidates -> Voyage reranker reorders top-N (e.g. 30 -> 10) -> return. The function already exists in the public API; this is wiring, not construction. Degrade gracefully when key absent (current behaviour).

### 5.2 Hybrid lexical channel ✓ 8f7d1ab
Replace the +0.1 substring boost with BM25 over name/description/observations (pure-Python, e.g. `rank-bm25`, or Neo4j full-text index at L2b). Fuse via reciprocal rank fusion with the vector channel. Substring match is brittle for exactly the structured queries the system claims to serve.

### 5.3 Progressive disclosure for L0 ✓ adc8c71
MEMORY.md lines gain optional category grouping with one-line headers; the always-loaded index points to retrieval, it does not substitute for it. Combined with the Phase 1 token budget this aligns L0 with just-in-time retrieval rather than front-loading.

**Files:** `store.py`, `neo4j_store.py`, `embeddings.py`, `consolidation.py`, hook script.

---

## Phase 6: Evaluation Harness ✓ 6cfa4d5

**Problem:** 390 unit tests, zero retrieval-quality measurement. All scoring parameters are untested hyperparameters.

- `tests/eval/` — fixture store (~200 synthetic entities across scopes, types, hierarchy levels, provenance classes) + query set with gold relevant-entity labels.
- Metrics: recall@k, MRR, nDCG@10; reported by `memoryschema eval` and tracked in CI (regression threshold, not absolute gate).
- Temporal-reasoning and multi-session cases modelled on LongMemEval task categories (information updates, knowledge spanning sessions, abstention when memory absent).
- **Poisoning red-team suite:** inject MINJA-style entries into the fixture store (plausible-looking `ingested` entries containing instructions); assert (a) they never reach MEMORY.md, (b) they retrieve only inside untrusted delimiters, (c) trust weighting ranks them below first-party equivalents.
- A/B the Phase 2 weight changes against this harness before merging.

**Files:** `tests/eval/` (new), `cli/eval_cmd.py` (new), CI config.

---

## Schema v3 Summary

| Change | Kind |
|---|---|
| `status` attribute (active/superseded/archived/quarantined) | New optional |
| `provenance` attribute (first-party/user/ingested/derived) | New optional |
| `PARENT_OF`, `CHILD_OF` | Deprecated (read-accepted, server-derived) |
| R2 corrected; R6 (referential integrity) added | Validation |
| Embedding-input specification | New section |
| Full scoring formula (incl. hub bonus, text/BM25 channel, type factor, trust multiplier) | Consolidated into schema.md |
| Audit log behaviour (On Mutate) | Behavioural spec |
| v1/v2 files | Remain valid |

## Issue-to-Phase Traceability

| # | Issue | Phase |
|---|---|---|
| 1-4 | Doc drift (R2, scoring fork, test counts, doctor counts) | 0 |
| 5 | Inert type system | 2.2 |
| 6-7 | SUPERSEDES/CONTRADICTS unconsumed | 1.2 |
| 8 | No delete/archive | 1.3 |
| 9 | MEMORY.md overflow | 1.4 |
| 10-11 | Importance=scope; write-everything rule | 2.1 |
| 12 | Rich-get-richer | 2.3 |
| 13 | Destructive upsert, no history | 3.4 |
| 14 | Dangling relations | 1.3 (R6) |
| 15 | Embedding input unspecified | 2.4 |
| 16 | Dual hierarchy encoding | 4.1 |
| 17 | Sibling-prefix bug | 4.2 |
| 18 | Over-fetch shortfall | 4.3 |
| 19 | Precedence inversion | 4.4 |
| 20 | JSONL concurrency | 4.5 |
| 21-22 | No provenance; L0 injection channel | 3.1-3.2 |
| 23 | No audit trail | 3.4 |
| 24 | Prompt retention / egress / default password | 3.5 |
| 25 | Parent-rules trust direction | 3.5 |
| 26 | No retrieval evaluation | 6 |
| 27 | Reranker unused | 5.1 |
| 28 | No L0 token budget | 1.4, 5.3 |

## Verification

1. `make docs-sync && git diff --exit-code docs/` — documentation generation clean (Phase 0).
2. Full suite green; new tests for status transitions, archive/delete, R6, dot-boundary, lock contention, precedence.
3. End-to-end: write A, write B with `SUPERSEDES -> A`; `recall` returns B only; `recall --include-superseded` returns both.
4. Poisoning suite: injected `ingested` instruction entity absent from MEMORY.md, retrieved only within untrusted delimiters.
5. `memoryschema eval` baseline recorded pre-Phase-2; weight changes show non-regression on recall@5 and MRR.
6. `memoryschema doctor` — all checks green, including new audit-log and rules-hash checks.
7. MEMORY.md token count <= budget after 500 synthetic writes (eviction working).

## Status: COMPLETE

All 7 phases (0-6), 25 sub-items implemented. 427 tests passing.
22 [S2] commits. Session report: `docs/reports/2026-06-09-session-report-7.md`

Residuals:
- reflect() CLI command deferred (callable from Python only)
- Neo4j max_depth resolved by Phase 4.6

## Sequencing and Risk

- Phase 0 is prerequisite-free; do first.
- Phase 1 before 3 (status field needed for quarantine) and before 2 (selective-write rule changes working-memory volume, which affects scoring evaluation).
- Phase 6 fixture can be built in parallel from Phase 1 onward; Phase 2 weight tuning is **blocked on** Phase 6.
- Highest-risk change: precedence reorder (4.4) — behavioural change for existing deployments; gate behind a `config_version = 2` TOML key with a deprecation warning for one release.
