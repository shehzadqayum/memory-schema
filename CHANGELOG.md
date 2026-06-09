# Changelog

## [Unreleased]

### Added
- `hierarchy.py` — dot-notation project hierarchy utilities (parse, ancestor, scope/filter)
- `inheritance.py` — TOML config loading, rules resolution with parent-wins authority
- `PARENT_OF`, `CHILD_OF` relation types for agent hierarchy edges
- `MemoryConfig.from_toml()` classmethod for TOML-based config with inheritance
- `memoryschema rules` CLI command — show effective rules with inheritance markers
- `memoryschema config` CLI command — show effective config with chain sources
- `memoryschema.toml` template generated on `memoryschema init`
- `max_depth` parameter on `project_matches_scope()` for bounded read-up
- `validate_toml_name()` advisory check for project name / directory mismatch
- `overridden_rules()` for detecting parent-shadowed child rules
- Doctor checks: `toml_config`, `rules_inherit` (now 20/20)
- `--project` option on `recall` and `search` CLI commands

### Changed
- `resolve_rules()` now returns `(effective, overridden)` tuple (single walk)
- Unscoped entities (None/empty project) are universally visible in scoped queries
- Store scoping uses module-level imports instead of repeated inline imports

### Fixed
- Neo4j status Docker detection — split availability from container status
- `init --with-neo4j` — duplicate config argument in `ctx.invoke`
- Doctor test check — cwd resolution, timeout (30s→120s), output parsing
- Fragile gap heuristic replaced with marker-based `_walk_upward()`
- Duplicate walk logic unified into shared helper
- Dual env var reads removed from `inheritance.py`
- `_name_warning` side-channel removed from config resolution dict
- Direct `os.environ` reads removed from `neo4j_store.py` and `embeddings.py` — centralized in `config.py`
- Env var precedence inversion in `from_toml()` — env vars now correctly override TOML values
- Redundant inline import in `store.py` `compute_associations()`
- **Cypher injection defense** — explicit ValueError on invalid relation types in `neo4j_store.py`
- **Neo4j unscoped entities** — `OR m.project IS NULL` in all 5 project-scoped queries
- **Type default** — `tags.py` now defaults type to `semantic` when omitted (was empty string)
- **Hook reliability** — exit 2 when both Neo4j and JSONL fail; stderr no longer suppressed
- **Upsert immutability** — `schema` and `filepath` excluded from merge (immutable after creation)
- **`_derive_project` validation** — segments validated as non-empty kebab-case
- **Scoring deduplication** — numpy path uses `_score_entry` with `precomputed_relevance`
- **Dead imports** — removed unused `os` and `discover_memory_files` from `tags.py`

### Changed (Session 5)
- `requires-python` bumped from `>=3.10` to `>=3.11` (for `tomllib` stdlib)
- Relation type constants consolidated — single source of truth in `config.py`
- Scoring formula: `_searchable_text()` extracted, `precomputed_relevance` param added

### Added (Session 8)
- `memoryschema reflect` CLI command — wraps `consolidation.reflect()` for episodic clustering and semantic summary synthesis
- `reflect` exported in `__init__.py` public API

### Added (Session 6)
- `docs/hierarchy-and-inheritance.md` — standalone feature reference (420 lines, 8 sections)
- `docs/plans/` — history directory for completed plan documents
- Scoring bonuses documented: hub `+0.05*min(backlinks,5)`, text match `+0.1`
- Cross-references to new reference doc from README, system-overview, tech-ref, impl-guide

### Added (Session 7 — v3 Remediation)
- **Schema v3:** `status` attribute (active/superseded/archived/quarantined), `provenance` attribute (first-party/user/ingested/derived)
- **Lifecycle:** SUPERSEDES consumption (auto-supersede targets), CONTRADICTS symmetry (auto-reverse), delete with full cleanup (MEMORY.md + .md file + inbound relations), archive command, R6 referential integrity validation
- **L0 budget:** MEMORY.md token budget (2000 default) with score-based eviction via `l0_budget.py`
- **Reflection:** `reflect()` function — clusters episodic entries, synthesises semantic summaries with LLM/mechanical fallback
- **Trust:** provenance field, trust-weighted retrieval (ingested=0.7x), L0 gating (ingested blocked from MEMORY.md), pre-consolidation write gate with consistency probe
- **Audit:** append-only `memory/audit.jsonl` with field-level change tracking
- **Hygiene:** per-project hook install (`--per-project`), random Neo4j password on init, rules hash attestation in doctor
- **Retrieval:** Voyage reranker wired into recall, BM25 lexical channel replacing substring boost, progressive disclosure with category grouping in MEMORY.md
- **Evaluation:** `tests/eval/` harness with 50-entity fixture store, recall@k/MRR/nDCG metrics, poisoning red-team suite, `memoryschema eval` CLI command
- **Concurrency:** advisory file lock (`fcntl`) for JSONL read-modify-write
- **Config:** `max_inherit_depth` (default 3), `l0_token_budget` (default 2000) — both TOML-configurable
- `scripts/docs_sync.py` — CI-ready documentation drift checker

### Changed (Session 7)
- Schema version bumped from 2 to 3
- PARENT_OF/CHILD_OF relation types deprecated (accept on read, warn on write)
- Config precedence reordered: CLI > env vars > parent TOML > child TOML > defaults
- Hub bonus: linear `0.05*min(bl,5)` → log-scale `0.05*ln(1+bl)`
- Type system active: semantic=no decay, episodic=standard, procedural=access-reinforced
- Importance decoupled from scope — full 1-10 range by salience
- Working memory: selective-write rule replaces mandatory every-response write
- Embedding input standardized: name+description+observations+prompt+reasoning (body excluded)

### Fixed (Session 7)
- Doctor Python version check: 3.10 → 3.11 (matches requires-python)
- Q8 strict-mode check for reasoning length (>500 words)
- V11 status validation, V12 provenance validation

### Fixed (Session 6)
- Doctor Python version check aligned to 3.11 (was 3.10)
- Doctor check count in tech-ref and impl-guide: 18 → 20
- Phantom `memory/user/<name>.md` path removed from schema.md
- Working memory importance: "8-10" → "10" in system-overview.md

### Changed (Session 6)
- `docs/plan-hierarchy-and-inheritance.md` moved to `docs/plans/` with superseded note
- tech-ref hierarchy/inheritance module rows now link to reference doc instead of inline function lists

### Removed
- `docs/plan-hierarchical-nesting.md` — consolidated into `plan-hierarchy-and-inheritance.md`
- `docs/plan-agent-inheritance.md` — consolidated
- `docs/plan-fix-6-inheritance-issues.md` — consolidated
- F2 validation rule removed from `docs/schema.md` (was never implemented)
