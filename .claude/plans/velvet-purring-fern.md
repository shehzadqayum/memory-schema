# Verification Axis, Gate Hardening, Subject Instrumentation

## Context

Document version 6. Seven motivating defects (D1–D7). Schema v4: verification axis (basis), gate probes (numeric contradiction with burn-in, L0 echo), MITIGATES with criterion capture, typed force records, salience instrumentation, report sequencing. v6 documents two accepted residual risks: Observation(str) enforceability limit (basis loss findable not prevented, docstring requirement for future modules) and qualifier-key missed-contradiction limit (documented in numeric_probe docstring). No design changes from v5. Prior: A1/A2 split, basis-loss rule+test, world-change coverage caveat, decay enum clarification, Phase 7 patch-spec default.

## Prior Residuals (from [S4] 9440915)

None.

## Execution Units

| Unit | Content | Exit criteria |
|------|---------|---------------|
| A1 | Pre-work P1–P3, Phase 0, Phase 1 — schema v4 structural layer | VC 1–2, 13–15 |
| A2 | Phase 2 — verification-aware scoring + guards + staleness | VC 3–4 |
| B | Phases 3–5 — MITIGATES, force record, gate stages 5–6, reflect | VC 5–8 |
| C | Phases 6–8 — decline, report sequencing, docs sweep | VC 9–12 |

Do not combine A1+A2 unless A1 closed early.

**Session 14 scope: Unit B (Phases 3–5).** Exit criteria: VC 5–8. ✓ complete.

**Session 15 scope: Unit C (Phases 6–8).** Exit criteria: VC 9–12. Resolves carried residuals R1 (hook stamp) + R2 (docs v4).

## Pre-Work P1–P3 ✓ 283b111

### P1. schema.md v3 summary rows
- Schema Versioning v3: append ", R7 (SUPERSEDES cycle detection)"
- Design Decisions v3: "Adds V11, V12, V13, R6, R7 validation rules."

### P2. schema.md overlapping upsert tables
- Consolidate into one table in Upsert Semantics; cross-reference at second location

### P3. technical-reference.md doctor table missing 3 checks
- Add: toml_config, rules_inherit, rules_hash (confirm against doctor_cmd.py)

## Phase 0 — Reconnaissance (read-only) ✓ 03f966a

| # | Confirm | Where |
|---|---------|-------|
| 0.1 | Observation storage shape | store.py, neo4j_store.py |
| 0.2 | Embedding timing vs gate stage 4 | write_gate.py, hook |
| 0.3 | SUPERSEDES trust guard site + Neo4j mirror | store.py, neo4j_store.py |
| 0.4 | Hook env var inheritance | hook script |
| 0.5 | Reflect cluster contents | consolidation.py |
| 0.6 | Recall rendering site(s) | cli/ recall |
| 0.7 | Neo4j text-match reads observations directly? → selects model | neo4j_store.py Cypher |

Record in commit. Follow §A fallbacks if false.

## Phase 1 — Schema v4 structural layer (D1, D5) ✓ 0e0b9f9

### 1.1 Schema document
- Version 4; v4 rows in BOTH summary tables
- basis on `<memory:observation>`: measured | inferred | reported (no default)
- Definitions: measured=command output/mechanical record; inferred=derived by reasoning; reported=carried forward
- Server-managed: verified_at, generator, embed_model
- V14 validation rule

### 1.2 Parser (tags.py) — Observation(str) subclass
- `class Observation(str)` with basis — IS a string, zero consumer sweep
- Construction discipline: __new__ only sanctioned constructor
- In-memory basis-loss rule: transforms return plain str. Code for comparison/display calls observation_text(); code retaining basis rebuilds via __new__. Bare→str flowing to stored state = defect.
- Accepted residual limit: convention not constraint; Python cannot prevent str(obs) bypassing tests. Basis loss is findable (unlabelled where labelled expected) not prevented. Future observation-handling modules MUST add own basis-preservation test — note in Observation docstring.
- Serialization: serialize_observation / deserialize_observation in tags.py; grep all json.dump/dumps
- CANARY TEST: no dict/JSON syntax leaks
- BASIS-LOSS TEST: mutate through string ops, assert explicit drop or preservation

### 1.3 Stores
- JSONL: serialize_observation; legacy byte-identical; no migration
- Neo4j: per 0.7 — preferred JSON-per-element or fallback parallel-lists (3 mitigations)
- Basis immutability; duplicate-text upgrade (higher rank upgrades + verified_at + audit basis_upgrade; lower/equal skips)
- verified_at: server-managed, on ≥1 measured (including upgrade)

### 1.4 Generator stamping
- config.py: generator_id, env MEMORY_GENERATOR, no TOML key
- Hook: read env, pass to store; embeddings.py: return model id; reembed updates

### 1.5 Validator
- V14; Q9 strict warning (≥3 obs, none labelled)

### 1.6 Tests
- basis parse, V14, legacy round-trip, serializer pair, canary, basis-loss
- relabel ignored+audited, upgrade matrix, verified_at
- Neo4j model tests, hook generator stamp

## Phase 2 — Verification-aware scoring and guards (D1, D2) ✓ f2032bd

### 2.1 Scoring
- Basis factor: measured=1.0, inferred=0.97, reported=0.93, neutral=1.0
- Both backends; config basis_multipliers

### 2.2 SUPERSEDES verification guard
- Rank = max among labelled obs; unlabelled=2
- Source ≥ target; same site as trust guard; both backends
- reported cannot supersede measured; audit verification-guard

### 2.3 Staleness presentation (no scoring effect)
- [VERIFIED Nd ago] / [VERIFICATION STALE: Nd]; config verification_staleness_days=7
- JSON: verified_at + verification_age_hours

### 2.4 Tests
- Parity: 3×2 matrix; guard: 9 combinations; rendering: 0d/6d/8d

## Phase 3 — MITIGATES, closure discipline, typed force record (D3) ✓ 14eeedb

### 3.1 Relation type
- MITIGATES (7 active, 9 total); update "six" → "seven" everywhere
- B remains active; no status change

### 3.2 Criterion capture on SUPERSEDES
- Copy target description into audit as criterion
- Guideline: supersede when addressing criterion; MITIGATES otherwise

### 3.3 Typed force record (ledger-capture)
- operation="force": force_type (contradiction|supersession|world-change|decay), level, source, target
- By-product: SUPERSEDES→supersession, CONTRADICTS→contradiction
- decay: enum completeness only; NEVER eagerly emitted
- CLI: memoryschema force --type world-change --target NAME
- Coverage honesty: sparse records, no natural trigger; absence ≠ no change
- No consumer; records accumulate

### 3.4 Criterion satisfaction: principled limit
- Similarity gate would PASS D3's false closure; achievable standard = capture + MITIGATES + audit

### 3.5 On Mitigate lifecycle
- Audit operation=mitigate; dampening mitigation_dampening (0.95)

### 3.6 Tests
- MITIGATES accepted; target active; dampening; criterion; force records

## Phase 4 — Gate extensions (D4, D5) ✓ c75dc50

### 4.1 Pipeline precondition
- Candidate embedding before stage 4; stages 5-6 skip when degraded

### 4.2 Stage 5 — Numeric contradiction probe (numeric_probe.py)
- extract_claims: quantity + unit + qualifier; key = (unit, qualifier)
- Qualifier limit (docstring): captures ONE token after unit; "472 tests currently passing" keys as (test, currently) not (test, passing); conservative = under-fire not over-quarantine
- compare: pure function, neighbours as argument
- numeric_probe_mode: "log" (default) | "quarantine"; never REJECT
- Escape: CONTRADICTS or SUPERSEDES bypass
- Extension point: compare() accepts neighbour set

### 4.3 Stage 6 — L0 echo probe
- Jaccard overlap ≥ threshold + no measured + no new relations → QUARANTINE
- memory:<name> source convention; source_is_memory audit flag

### 4.4 Tests
- ≥15 extractor cases incl qualifier; both modes; bypasses; echo 2×2; degradation

## Phase 5 — Contradiction-aware reflect (D4) ✓ e2460bc

- Check clusters for CONTRADICTS + numeric contradictions pre-synthesis
- Hit → skip; audit reflect_skip
- --include-contradictory: min importance, CONTRADICTS edges, inferred basis
- Uniform LLM + mechanical

## Phase 6 — Salience instrumentation (D6) ✓ 5e5aba3

- log_decline(name_hint, reason, context_hash)
- CLI: memoryschema decline --reason "..." [--name-hint X]
- Guideline with limitation caveat
- Eval: salience mode, ~20 fixtures, precision/recall

## Phase 7 — Report sequencing (D7) — in scope, outside package ✓ a3ade4e

- Default: patch spec (shared skills = shared risk)
- Direct edit ONLY if confirmed project-local
- Checkpoint: "as of checkpoint; close commit pending"
- Session-close: amend with final count + close pointer
- Backfill most recent; erratum convention
- Memory entities: basis="reported" → append measured after close

## Phase 8 — Documentation synchronization (single commit) ✓ ef6b2a6

- schema.md: all Phase 1/3/4 items; v4 rows; force record; memory:<name>
- Rules + templates: sync
- technical-reference.md: basis factor, configs, stages 5-6, force CLI, module table
- README.md: hook pipeline, gate verdicts, decline + force, relation count
- Doctor: generator_env + gate_probes (+ neo4j_observation_integrity if fallback); 21→23/24
- CHANGELOG: all phases + v4 rationale

## Verification Criteria

| # | Criterion | Unit |
|---|-----------|------|
| 1 | v1/v2/v3 round-trip unchanged | A1 |
| 2 | Basis immutable; relabel audited | A1 |
| 3 | Score parity basis × provenance | A2 |
| 4 | reported blocked from superseding measured | A2 |
| 5 | MITIGATES active; criterion; force records | B |
| 6 | Numeric probe modes + bypasses | B |
| 7 | Echo quarantine/accept | B |
| 8 | Reflect skip + flag path | B |
| 9 | Decline audit + salience eval | C |
| 10 | Phase 7 patch spec or marker+count | C |
| 11 | No services: probes skip, writes succeed | C |
| 12 | docs_sync; doctor count; P1-P3 | C |
| 13 | Canary: no syntax leaks | A1 |
| 14 | Basis upgrade + verified_at | A1 |
| 15 | Neo4j model invariant | A1 |

## §A Assumptions Register

| # | Assumption | If false |
|---|-----------|----------|
| A1 | String lists in both stores | Serializer adapts; Observation(str) survives |
| A2 | Embedding at gate time | Pre-gate refactor per 4.1 |
| A3 | One trust guard site | Place at actual choke point |
| A4 | Hook inherits env | Session-scoped dotfile fallback |
| A5 | Clusters have entities | Fetch from store |
| A6 | One rendering site | All sites + parity test |
| A7 | Searchable-text property | Parallel-list + 3 mitigations |

## Out of scope

- **Embedder axis** — deferred; only compare() extension point
- **Level axis + decay views** — reserved for future phases; derivable from plan's data; build none now
- **Staleness-coupled scoring** — presentation only; coupling behind eval harness
- **Mechanical criterion enforcement** — principled limit (Phase 3.4)
- **Ledger-capture exception** — Phase 3.3 force record lands NOW (world-change unreconstructable)
