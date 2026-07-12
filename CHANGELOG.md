# Changelog

## [Unreleased]

### Fixed (2026-07-12 — v5 parser silently truncated relations and unknown sections)
- **A stray line inside `relations:` no longer severs the block.** The parser exited relations mode on the
  first non-matching line; an indented stray bullet or comment then made every SUBSEQUENT `- TYPE target`
  fall through the scalar guard and vanish — and the next programmatic rewrite erased them permanently. The
  mode is now Postel-liberal: an indented / bulleted / blank / comment line is SKIPPED (mode retained); it
  exits only on a genuine top-level `key:` scalar (column 0).
- **Lowercase relation types parse instead of vanishing.** The relation-line regex widened from `[A-Z_]+` to
  `[A-Za-z_]+` (a documented superset of the canonical UPPERCASE set), so a `- uses x` now PARSES and the
  validator flags it loudly as **R2** — parse-liberally / validate-strictly, not a silent drop.
- **Unknown `## Heading` sections are preserved verbatim on roundtrip.** They were parsed but the serializer
  re-emitted only the six known sections, so an invented section was destroyed on the next append/lifecycle
  rewrite. The parser now collects them (first-seen order, original title case) into `extra_sections` and the
  serializer re-emits them after the known sections. They still carry no machine semantics.
- **Writers refuse a silently-shrinking rewrite.** `append_chain_step` (v5) and `set_lifecycle` now assert,
  after serialize, that the re-parse retains at least as many relations and the same unknown-section titles —
  a shrink raises and leaves the file unchanged (defense-in-depth beyond the well-formedness check).
- Docs: schema-specification §2 rewritten (relations mode + unknown-section preservation); new
  `tests/test_format_v5_fuzz.py` malformed-input battery. Additive — no `SCHEMA_VERSION` bump.

### Fixed (2026-07-12 — a JSONL merge dropped new vectors; packaging clash with strict resolvers)
- **`embed_input_hash` now merges with the vectors (retrieval was scoring new text against old embeddings).**
  The JSONL merge whitelist carried `embedding`/`embeddings`/`divergence_profile` but NOT `embed_input_hash`,
  the sidecar's skip-if-unchanged key. So a merge carrying NEW vectors kept the OLD stored hash, `externalize()`
  saw a match and SKIPPED the `.npz` rewrite — the new vectors were dropped, and recall scored the updated
  content against the stale embedding until the next `reconcile`. Added the hash to the whitelist (it is
  computed together with the vectors by `embed_all_spaces`); new end-to-end test asserts the sidecar is
  actually rewritten on a merge. Removed the corresponding "known consequence" note from the manual.
- **`[embeddings]`/`[all]` now resolve under strict resolvers (Poetry 2.x / uv).** `voyageai` caps its own
  Requires-Python at `<3.15`; our `requires-python` is unbounded `>=3.11`, so a whole-range solver could not
  find a `voyageai` valid for 3.15+. Added the marker `python_version < '3.15'` to the voyageai requirement in
  both extras — on a future 3.15 the extra installs everything else and embeddings degrade loudly (lazy
  import). No upper bound on `requires-python` (the base install is click-only).

### Fixed (2026-07-12 — Neo4j SUPERSEDES cycle detection persisted the cycle it rejected)
- **The Neo4j store checked for a SUPERSEDES cycle AFTER committing the edge.** `upsert` ran
  `MERGE (s)-[:SUPERSEDES]->(t)` (auto-committed), then the R7 cycle query, then raised `ValueError` on a
  cycle — leaving the cyclic edge persisted in the graph. So a rejected write still corrupted the store, and
  the two backends diverged (the JSONL store pre-validates against its in-memory snapshot and aborts cleanly).
  Moved the cycle check ABOVE the `MERGE` (SUPERSEDES only). Order-independent: the query searches for a
  *pre-existing* path `t -[:SUPERSEDES*]-> s`, which never contains the not-yet-created `s -> t` edge, so the
  answer is identical — but a rejection now leaves the graph clean. Added the first cycle tests for BOTH
  backends (hermetic JSONL + an integration test asserting the poison edge is not persisted), closing a
  zero-coverage gap that let the asymmetry survive.

### Fixed (2026-07-11 — retrieval-scoring config knobs were silent placebos)
- **`recency_decay`, `mitigation_dampening`, `recall_depth`, `recall_decay` now actually take effect.** All
  four were config fields (TOML-mappable) but the scorers hardcoded the literals (`0.995` / `0.95`) and the
  CLI `recall` never passed depth/decay — so setting them in `memoryschema.toml` did nothing, contradicting the
  module's "degrade loudly / no silent no-op" doctrine (and the `semantic_weights` knob in the same file DID
  work, making the gap surprising). Both stores' `_score_entry` now read `self.config.recency_decay` /
  `mitigation_dampening` (falling back to the same literals when `config is None`), and CLI `recall` passes
  `config.recall_depth`/`recall_decay` to the cascade. **No default behaviour change** — `config=None` and a
  default `MemoryConfig` reproduce the historical `0.995`/`0.95` (pinned by a test). The three now-stale
  "hardcoded" caveats in the harness manual are corrected.

### Added (2026-07-11 — deployment architecture + the machine-stamped ledger)
- **`memoryschema deploy register` / `deploy status`** + **`DEPLOYMENT.md`** — the git-sharing architecture:
  a single-source-of-truth module repo, `git subtree` vendoring, per-project `deployments/<project>` branches,
  and a **machine-stamped ledger** (`deployments/<project>.toml` on `main`). `register` deterministically
  stamps the pointer + module HEAD + schema version + date; `status` reconciles the ledger files against the
  actual `deployments/*` branches and flags any disagreement (registered-not-pushed / branch-only), so the
  ledger can never silently drift from git — unlike a hand-maintained registry. Hermetic tests (throwaway git
  repo). Rationale + rejected alternatives (PyPI-registry, submodules) documented in DEPLOYMENT.md.

### Added (2026-07-11 — the adoption guide)
- **`BOOTSTRAP.md`** — how to adopt the module in a new or existing project, written from the verified path:
  prerequisites, the two install modes (pip vs git-subtree vendor), `init` (what it scaffolds), `hook install`,
  `plugin sync` (+ `--check` drift gate), backend up + `preflight`, first-memory habits, a verification
  checklist, and an upgrade/troubleshooting section. Linked from the README quickstart.

### Changed (2026-07-11 — project-agnosticism: the package no longer references any specific deployment)
- **The entire package is now project-agnostic — zero references to any deployment (no "Helios", "Aurora",
  "trading-journal", or trading-domain examples) in any live file** (code, tests, deployed rules/skill, docs).
  Toward a truly standalone, reusable module:
  - Comments: removed the ~35 "helios local patch — re-apply on re-vendor" / "(helios local patch)" markers
    across src + tests (the re-vendor premise dissolved under the canonical-source doctrine); comment-only.
  - Deployed artefacts (ship to every project): dream-pass skill + on-demand rules genericized
    (`project: my-project`, generic key/relation examples, "tune via `retrieval.semantic_weights`", no
    `.venv/Scripts` assumption).
  - `l0_token_budget` module default 3000 → **2000** (the honest default); a deployment raises it via
    `retrieval.l0_token_budget` in its `memoryschema.toml` (behaviour-preserving for deployments that already
    set it).
  - The eval gold set is externalized: `fixtures.build_helios_gold_set` → a generic `build_gold_set` (smoke)
    plus `load_gold_set(path)` that reads a deployment-supplied JSONL (e.g. `<project>/eval-gold.jsonl`), so no
    corpus-specific data lives in the package.
  - Docs (README, harness-manual, docs/README) + the package CLAUDE.md: genericized the deployment examples,
    corrected the false "hook upgrade overwrites the script" claim, and removed the Helios-specific operating-
    context appendix (deployment specifics belong with the deployment).

### Changed (2026-07-11 — standalone deployability: the plugin artefacts install & unify)
- **M1 — `plugin sync` / `plugin deploy` now work from a real `pip install`.** The deployable-artefacts SSOT
  lived at the repo root (`.claude-plugin/`) and was packaged by nothing, so `_find_plugin_dir()` resolved it
  only in a source checkout — a wheel install exited 1 ("source of truth missing"). Moved it UNDER the module
  to `src/memoryschema/claude_plugin/` (shipped as `package-data`), and `_find_plugin_dir()` now resolves it via
  `importlib.resources`, so it works from any install. Verified end-to-end: built a wheel, installed it into an
  isolated venv (no source tree), and `plugin sync` deployed all four artefacts from `site-packages`.
- **M2 — `init` and `plugin sync` deploy from ONE source.** `init` used to write rules from `templates/*.tpl`
  while `plugin sync` wrote the same logical artefacts from the plugin dir — two divergent kernels for one
  path, and a schema ref duplicated across two load tiers. Both now call a shared `deploy_artefacts` over the
  single `claude_plugin/` source; `init --scopes` selects the on-demand rule set. Deleted the three orphaned
  templates (`memory-working.tpl`, `memory-schema.rules.tpl`, `memory-corpus.tpl`). Re-running `init` is now
  CONVERGENT for the `.claude/` artefacts (re-synced from the package like `plugin sync`, so a locally-edited
  deployed rule heals back); the non-artefact files (compose/.env/toml) are still create-only.
- **Examples rewritten to v5.** `examples/ingest_tweets.py` / `ingest_forum.py` now author entities via
  `write_index.create_entity_file` (v5, no manual XML/escaping) instead of hand-built `<memory:entity
  schema="4">`; `consolidate_working.py` uses `format_v5.serialize_v5` (it carries a `prompt` section the plain
  create path doesn't take). Removed the `xml.sax` escaping imports and the dead `schema: 2`.

### Fixed (2026-07-11 — adversarial-review follow-ups on Part B/C)
- **B3 corruption marker was both too broad AND too narrow.** `_V5_SCHEMA5_MARKER` scanned the whole file
  (`re.MULTILINE`), so a non-entity note whose *body* contained a `schema: 5` line was misclassified as a
  corrupt entity and aborted the entire reconcile (false positive); it also missed a quoted `schema: "5"`
  that the parser accepts, so a corrupt quoted-schema file evaded the guard and was silently pruned (false
  negative). Replaced with `_declares_v5_in_frontmatter`, which **delegates to `format_v5._parse_frontmatter`**
  (the same parser `parse_v5_content` uses) and applies its exact discriminator — so the guard cannot drift
  from what the parser accepts across quoted / `schema :` / indented spellings. All cases tested.
- **`init` .env/.gitignore append was not newline-safe.** Appending `.env`/`NEO4J_PASSWORD=…` to a file whose
  last line lacked a trailing newline glued the entry onto the prior line (`.env` never ignored → secret
  committable; or a corrupted `.env` key/value). Appends now insert a leading newline when needed.
- **v5 validation parity:** `_validate_v5` now flags a non-integer `importance` (which the parser silently
  drops) exactly as the v4 path does.
- **Docs synced to the landed code:** the schema-spec §3 corruption/quality notes, the harness-manual
  `SCHEMA_VERSION`/env-var/`corrupt-v5` caveats, and the on-demand rule source-of-truth pointers no longer
  describe B1/B3/B4 as pending or `SCHEMA_VERSION` as `4`.
- **Honesty:** preflight's compose-trust-gate comments now state it is an anti-footgun, not an adversarial
  boundary (the sentinel is a copyable token). Added regression tests for the trust gate, the hook `.env`
  allowlist, the V10 v4-ceiling boundary, and the B1 Q6/Q7 log-slice.
- **Final-state coherence pass (fresh-eyes review of the whole arc):** fixed doc/comment staleness in sections
  no delta had touched — harness-manual §9.3 reconcile step (pre-B3 v5 caveat) and §11 `validate` CLI row
  (pre-B1 "v5 files report V1"), `validator.py` module docstring ("v4 XML only"), and the reconcile
  malformed-guard comment + operator abort message ("Fix the XML" → both formats). No behavior change.
- **Pre-extraction coverage batch:** added the deferred `_validate_v5` branch tests (V3 filename-mismatch, F3
  unsafe-name, R6 referential-integrity, Q8 reasoning length, V5 importance range) and the B2 both-set-env
  precedence case; removed the unreachable `V2` branch in `_validate_v5` (the parser guarantees a name).

### Security (2026-07-11 — pre-extraction hardening, Part C)
- **HIGH — preflight no longer auto-runs an untrusted compose file.** `preflight._start_container` ran
  `docker compose -f <cwd>/docker-compose.yml up -d` unconditionally, so invoking any memoryschema command
  inside an untrusted directory could `up` a hostile `docker-compose.yml` (arbitrary services/volumes/
  entrypoints). It now (1) tries `docker start <container>` first — recovering a stopped container while
  executing NO file — and (2) falls back to `compose up` ONLY when the file is memoryschema-generated
  (carries a `memoryschema-managed` header sentinel), refusing an unrecognized CWD compose. The generated
  template and the deployment compose carry the sentinel.
- **HIGH — the post-write hook no longer exports the entire `.env`.** `hook-post-write.sh` loaded the
  project `.env` and `export`ed *every* key into the indexer child process — leaking unrelated secrets
  (cloud tokens, other services) far beyond the DB/embedding credentials it needs. The export is now
  allowlisted to the memory backend's own namespaces (`NEO4J_*`, `VOYAGE_*`, `MEMORYSCHEMA_*`,
  `MEMORY_PROJECT`, `MEMORY_GENERATOR`, `MEMORY_ROOT`).
- **MED — `init` no longer bakes the Neo4j password into the generated compose.** `docker-compose.yml.tpl`
  rendered `NEO4J_AUTH=neo4j/<plaintext>` (and the healthcheck) with the generated secret at rest in the
  file. The template now references `${NEO4J_PASSWORD}`, and `init` persists the generated secret to the
  sibling `.env` (creating/extending `.gitignore` to exclude it) so `docker compose up` interpolates it and
  the CLI/hook — which already auto-load `.env` — pick it up. Matches the helios deployment fix (`310a42e`).

### Changed (2026-07-11 — schema-split Part B: the harness conforms UP to the entity authority)
- **B4 — `SCHEMA_VERSION` reflects the current format.** It was pinned at the legacy v4 marker (`4`) while
  entities carry `schema: 5`, so the schema mis-reported its own version. `SCHEMA_VERSION` now equals
  `CURRENT_ENTITY_FORMAT` (`5`); a new `V4_XML_SCHEMA_VERSION = 4` carries the legacy v4-XML `schema=`
  attribute upper bound used solely by the validator's V10 range check (a v4 file is never "schema 5" — v5 is
  a different format, not XML). `config.schema_version` is now `5`. The B4 conformance test is no longer an
  xfail — all four Part-B placeholders are now real passing tests.
- **B2 — v5 is now the authored default.** `create_entity_file` (and therefore `remember` / new entities)
  emitted **v4 XML** unless `MEMORYSCHEMA_V5=1` — the harness authored the *superseded* format by default. It
  now authors **v5 by default**; v4 XML authoring is retained only for legacy/migration behind an explicit
  opt-out (`MEMORYSCHEMA_V4=1` or `MEMORYSCHEMA_V5=0`), and v4 files still parse unconditionally. Deployments
  that set `MEMORYSCHEMA_V5=1` (incl. helios) are unaffected. Spec §1 write-side note updated; the v4-specific
  tests opt into v4 explicitly; the B2 conformance placeholder is now a real test (default v5 + opt-out v4).

### Fixed (2026-07-11 — schema-split Part B: the harness conforms UP to the entity authority)
- **B1 — v5 entities are now validated.** `validate()` counted `<memory:entity` tags and returned a spurious
  `V1 "no entity"` on any v5 file, so v5 entities bypassed every V/R/Q rule (and `memory validate` rejected
  *every* v5 file). It now dispatches on `is_v5_content` to a new `_validate_v5` that runs the content /
  relation / quality invariants (V2/V3/V5/V11, Q1/Q2/Q6/Q7/Q8, R1–R6, F3) on the parsed dict, reusing the v4
  rule IDs and the `entity_schema` grammars. XML-structural rules (V1/V6/V9) don't apply — v5 well-formedness
  is parse-success; a `schema: 5` file that won't parse returns a single `V1` well-formedness error.
- **B3 — malformed v5 files are guarded, not pruned (data-loss fix).** `reconcile._parse_md`'s
  corruption guard keyed only on the v4 `<memory:entity` tag, so a v5 entity whose frontmatter fence
  broke parsed to nothing and was treated as a deletion — reconcile then pruned its store/graph entry.
  The guard now also flags a `---`-fenced file that declares `schema: 5` but fails `parse_v5_content`
  as corruption (abort, never prune); a plain non-entity frontmatter note (schema ≠ 5) is still skipped.
  The `test_b3_malformed_v5_is_guarded_not_pruned` conformance placeholder is now a real hermetic test.
  Authority: `docs/schema-specification.md` §3 (corruption invariant).

### Added (2026-07-07 — mechanical, MD5-verified artefact sync)
- `memoryschema plugin sync [--check] [--target] [--global]` — deploys the canonical
  memory artefacts from the package into a project's `.claude/` as a verifiable derived
  copy, MD5-comparing each source against its deployed copy (writes only what differs;
  `--check` reports drift and exits non-zero without writing — a CI/session-start gate).
  Helios's session-start self-heal (`ensure-deps.ps1`, new `-NoSync` opt-out) runs the
  check each session and warns on drift. Spec §12.1.

### Fixed (2026-07-07 — operational artefacts are now packaged & deployable)
- The runnable operating system (the `dream-pass` skill + the kernel + the on-demand
  rules) is now versioned in the package at `.claude-plugin/` — previously the skill
  existed only in the deployment's `.claude/` and was absent from the package entirely.
- `plugin deploy` REPAIRED: it referenced a non-existent `.claude-plugin/` dir and a
  declared skill set (recall/chain-start/…/bootstrap) that shipped no files — the command
  could not deploy anything. Now the dir exists and `SKILL_FILES`/`RULE_FILES` reference
  the real artefacts (dream-pass skill; kernel → `rules/`; v5 + corpus refs →
  `rules-ondemand/`). Documented in spec §12.1 with the package-source-vs-deployment-local
  split (machine/ops artefacts — the SessionStart hook, ensure-deps.ps1, tuned toml —
  stay deployment-local by design).

### Added (2026-07-01..05 — Schema v5 & the deterministic write path)
- **Schema v5**: YAML frontmatter (machine scalars + `relations:` block) + markdown body
  (description lead, `## Summary/Observations/Log/Reasoning/Prompt/Chain/Notes`) —
  `format_v5.py`; `schema: 5` discriminator; name from filename; prose never enters a
  structured layer (the M14 XML-corruption class is impossible by construction). v4 XML
  still parses via `tags.py` dispatch; v5 creation gated on `MEMORYSCHEMA_V5=1`; the
  Helios corpus fully migrated.
- **Deterministic write path** (`write_index.py`): `memoryschema remember` (--desc/--obs/
  --type/--importance/--reasoning/--uses/--informs/--supersedes/--key/--valid-from) and
  `memoryschema chain step --stdin [--desc][--reasoning][--uses]` — plain text in; code
  escapes, auto-numbers, serializes with round-trip validation/rollback, and self-indexes
  with **dual-write to Neo4j AND JSONL** (replaces the hook's either/or drift). First
  chain step bootstraps the chain file (v5 skeleton).
- **Temporal validity**: fact keys (`--key`) with deterministic write-time supersession
  (`find_active_by_key`), `valid_from`/`superseded_at`/`superseded_by` interval fields,
  `recall --as-of` point-in-time filtering, and **file-first lifecycle**
  (`set_lifecycle` writes status/temporal/`promoted_to` into frontmatter so `reconcile`
  cannot resurrect archived/superseded entities).
- **Vector sidecar** (`vector_sidecar.py`): embeddings externalized to
  `memory/.embeddings/<name>.npz` (store.jsonl was 8.4 MB / 91.5% vector JSON →
  ~0.7 MB); hash-gated rewrite; transparent rehydration; pure-inline fallback sans numpy.
- **Recency-biased embedding composition** (`embedding_input.py`): `DEFAULT_MAX_CHARS`
  2000→8000; observations/reasoning truncate from the tail (newest first, first-obs
  anchor); `embed_input_hash` provenance (sha256 of the full untruncated composition)
  drives sidecar skip-if-unchanged and reconcile stale-detection; all 7 spaces embedded
  in ONE batched Voyage call.
- **Dream pass** (`dream_report.py`, `memoryschema dream`): read-only consolidation
  candidate report — released chains, oversized active chain (>40 obs), stale keyed
  facts (≥14 d), never-surfaced (7-day grace), near-duplicates (cosine ≥0.80),
  attribution review, promotion candidates. Judgment + actions live in the /dream-pass
  skill.
- **Attribution sampling** (`attribution.py`, `memoryschema attribution`): citation log
  (`.memoryschema/citation_log.jsonl`) written the moment `--uses`/`--informs` execute;
  joined against the recall log (24 h window) → per-memory attribution_rate; recall
  telemetry (`recall_log.py`, `memoryschema recall-stats`).
- **Skill promotion**: `promoted_to` frontmatter field via `set_lifecycle`; both store
  merge whitelists extended with the five lifecycle/temporal fields (a whitelist miss
  silently dropped them on updates to existing entities — found live, fixed with
  regression tests).
- **Ops**: `memoryschema preflight` dependency gate (+ implicit throttled CLI gate,
  container auto-start), `sync` read-only name-set drift, `reconcile` three-layer heal
  (malformed + shrink guards, provenance-hash re-embed, atomic writes, L0 rebuild);
  `l0_budget.rebuild_index` full-regenerate replaces append+evict; `.env` autoload in
  CLI and hook; hook Windows-path patch; injection kernel rewrite (~534 tokens).

### Changed (2026-07-05 — Documentation audit)
- `docs/harness-manual.md` rebuilt as **the single source of truth**
  (rebuildable-from-scratch spec: schema, write path, storage, retrieval, telemetry,
  consolidation, ops, config, complete CLI, test map).
- Deleted `docs/schema.md`, `docs/technical-reference.md`, `docs/implementation-guide.md`,
  `docs/system-overview.md` (superseded by the specification; see git history).
- README rewritten (v5 quickstart; fixed the `init --project` invocation, hook-pipeline
  order, degradation claims, test counts); `docs/design/` + `docs/plans/` bannered
  historical; hierarchy-and-inheritance updated (max_inherit_depth=3, Neo4j depth
  post-filter, escalating over-fetch); hook comments now cite the spec §9.4;
  doctor "21-point" labels and the pyproject "XML-based" description corrected.

### Fixed (Consumer Project Compatibility)
- Hook Python path: replaced hardcoded user-specific path with portable resolution chain (argument > env var > auto-detect > bare python3). `hook install` and `plugin deploy` embed `sys.executable` in the hook command.
- Doctor test check: now targets the memory-schema package's own tests instead of the consumer project's tests when invoked from another project. Excludes `test_cli_doctor.py` from the subprocess pytest to prevent infinite recursion.
- Docker detection: `neo4j deploy` and `neo4j status` use `shutil.which` with fallbacks to common locations instead of bare `docker` command that fails in pyenv/poetry environments
- Neo4j test mocks: updated `test_cli_neo4j.py` to mock `_find_docker()` instead of bare `subprocess.run` after Docker detection refactor
- Hook check: `validate_hook_python()` now extracts Python path from settings.json command args (fallback after script scan), fixing 7/8 → 8/8 after portable Python path change

### Changed (Templates)
- Synced `memory-working.tpl` and `memory-schema.rules.tpl` from deployed global rules — templates now include chain lifecycle, Edit-not-Write, reasoning accumulation, Write|Edit enforcement, Stop hook docs

### Added (Hook Management System)
- `memoryschema hook upgrade` — upgrade stale installations (Write→Write|Edit, add Stop hook) with `--dry-run` and `--per-project` flags
- `memoryschema hook check` — 8 diagnostic checks (script existence, executability, Python interpreter, dry-run both hooks, sentinel writable) with `--json` output
- `memoryschema hook scan` — cross-project hook installation discovery with version table and `--json` output
- `HOOK_VERSION` constant for version tracking (v0=not installed, v1=Write only, v2=Write|Edit+Stop)
- `get_hook_registration_detail()` — core inspection function for staleness, script health, upgrade needs
- `upgrade_hooks()` — in-place upgrade of stale hook registrations
- `find_project_settings()` — scan directories for .claude/settings.json files
- `validate_hook_python()` — check Python interpreter referenced by hook scripts
- `dry_run_post_tool_use_hook()` / `dry_run_stop_hook()` — non-destructive hook testing

### Added (Chain Reasoning)
- Chain reasoning accumulation: `<memory:reasoning>` now appends with `---` separator for chain-* entities (preserves narrative evolution). Standalone entities retain replace behavior.

### Added (Hook Consolidation)
- `src/memoryschema/cli/_hooks_util.py` — shared hook management module with `HOOK_MATCHER`/`LEGACY_MATCHERS` constants and 8 utility functions (path resolution, settings I/O, hook registration/removal)
- `tests/test_hooks_util.py` — 25 tests for shared hook utilities
- Hook Output Formats section in `docs/technical-reference.md` — documents valid JSON fields per event type

### Changed (Hook Consolidation)
- `hook_cmd.py` refactored to import from `_hooks_util` (removed 3 inline functions, net -91 lines)
- `plugin_cmd.py` refactored to import from `_hooks_util` (removed 7 inline functions, net -128 lines)
- `doctor_cmd.py` and `main.py` use `LEGACY_MATCHERS`/`HOOK_MATCHER` constants instead of magic literals
- Settings backup (`write_settings(backup=True)`) now applied consistently in both hook and plugin commands

### Added (Test Coverage)
- `tests/test_cli_plugin.py` — 42 tests for `plugin_cmd.py` (deploy, uninstall, status commands + 10 helper functions). Resolves residual carried since session 24.

### Added (Chain Enforcement)
- Stop hook (`hook-stop.sh`) — reminds Claude to update the active chain entity when no memory write occurred during a response
- Sentinel mechanism (`/tmp/claude-memory-chain-updated`) — PostToolUse hook touches sentinel on memory writes, Stop hook checks for it
- Stop hook registration in `hook_cmd.py` install/uninstall/status and `plugin_cmd.py` deploy/uninstall
- Stop hook health check in `doctor_cmd.py`

### Fixed (Chain Enforcement)
- Stop hook: replaced invalid `hookSpecificOutput.additionalContext` with `systemMessage` — `hookSpecificOutput` is only valid for PreToolUse, PostToolUse, and UserPromptSubmit events

### Changed (Chain Enforcement)
- PostToolUse hook matcher widened from `Write` to `Write|Edit` — Edit-based chain updates are now indexed
- Hook detection uses `in ("Write", "Write|Edit")` for backward compatibility with existing installations
- Chain lifecycle docs updated with Edit-not-Write guidance (schema.md, memory-working.md, memory-schema.md, memory-working.tpl)

### Added (Claude Code Plugin)
- `.claude-plugin/` directory with plugin manifest (`plugin.json`)
- PostToolUse Write hook registration (`hooks/hooks.json`) using `${CLAUDE_PLUGIN_ROOT}` path
- Hook symlink to `src/memoryschema/hooks/hook-post-write.sh` (development mode)
- Rules: `memory-schema.md` and `memory-working.md` copied to plugin
- Skills: `/recall`, `/chain-start`, `/chain-status`, `/chain-release`, `/memory-status`
- Hybrid memory scope: hook falls back to `~/.claude/memory/` when no project root derivable
- Recall dual-store search: project store first, user-level fallback for cross-project knowledge
- Plugin README with architecture, prerequisites, installation, quick start
- Project README updated with Claude Code Plugin section
- `memoryschema plugin deploy` — deploy skills, rules, hook to `~/.claude/` with manifest
- `memoryschema plugin uninstall` — clean removal using manifest (supports `--keep-data`)
- `memoryschema plugin status` — deployment health check
- `/bootstrap` skill — scan project docs and source after init, create knowledge map as interconnected memory entities (7-phase procedure, 8-22 entities, hub-and-spoke relation graph)

### Changed (Content-Agnostic Architecture)
- Removed provenance system (VALID_PROVENANCES, TRUST_LEVELS, trust multiplier, L0 gating, SUPERSEDES trust guard)
- Removed basis system (Observation subclass, VALID_BASES, VERIFICATION_RANKS, basis factor, verified_at, V14, Q9)
- Removed source field from entity schema
- Observations are now plain strings (no per-observation metadata)
- Added `confidence` attribute (integer 1-10, author-declared, scored as confidence/10 multiplier)
- Gate pipeline: 6 stages → 4 stages (validation, consistency, numeric, L0 echo)
- SUPERSEDES retains cycle detection only (no trust or verification guards)

### Added (7-Space Architecture)
- 7 embedding spaces: default + name + description + observations + prompt + reasoning + chain
- 1:1 field-to-space mapping (each field has its own embedding space)
- Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no base weights, no heuristics
- Divergence profile computed at embed time (structural fingerprint per entry)
- `chain` field on entities for reasoning chain context
- Chain entities: live accumulating memories with authorised/unauthorised states
- `memoryschema chain start/release` CLI commands
- Authorisation gate in hook: only active chain writable, all others read-only
- Free-form `type` attribute (no predefined values enforced by validator)

### Fixed (Framework Hardening)
- Hook: skip non-entity files (YAML frontmatter) instead of blocking with exit 2
- Reflect: `_cluster_by_associations` score threshold (0.7) fixes 0-cluster bug from giant connected component
- Neo4j: auth failure now raises ConnectionError with actionable message instead of raw driver error
- Neo4j: deleted orphaned test entries (`imported`, `test`), stores in sync at 34/34
- Hook: pass config to embed_text — embeddings now work via TOML api_key, not just env var

### Added (Framework Hardening)
- `tests/test_l0_budget.py`: 22 tests for token budget enforcement (was the only untested module)
- `tests/test_e2e_pipeline.py`: 10 tests covering write -> gate -> store -> recall + hook pipeline
- Neo4j integration tests with `pytest.mark.integration` marker (deselected by default)
- `--score-threshold` CLI option for `memoryschema reflect`

### Added (Multi-space — M1, NO SHIP)
- Field-level embedding spaces: `observations` and `reasoning` in embedding_input.py
- Space registry: 3 spaces (default, observations, reasoning) in spaces.py
- Multi-space scoring: `_multi_space_relevance()` in store.py with coverage-aware combiner
- Multi-space numpy batch path in `_score_all_entries`
- Per-space reembedding: `memoryschema embed --all --space observations` CLI option
- Structural absence handling: entries without observations/reasoning skip those spaces
- `EXPERIMENT_WEIGHTS = None` constant for explicit experiment configuration
- Gating experiment result: multi-space nDCG 0.601 < single-space 0.608, NO SHIP

### Added (v4 — Unit C)
- `log_decline()` in audit.py — write decline records for salience instrumentation
- CLI: `memoryschema decline --reason "..." [--name-hint X]` — frictionless decline recording
- CLI: `memoryschema force --type world-change --target NAME` — typed force events
- Guideline amendment: write decline instrumentation section in memory-working.md
- Report sequencing patch spec: docs/plans/phase-7-skill-amendments.md

### Added (v4 — Unit B)
- MITIGATES relation type (7 active, 9 total) — target stays active, no status change
- Mitigation dampening: 0.95 score multiplier for entries with inbound MITIGATES (both backends)
- Criterion capture: target description stored in audit record on SUPERSEDES
- Typed force records: operation="force" with force_type/level/source/target in audit.jsonl
- CLI: `memoryschema force --type world-change --target NAME` for unreconstructable events
- Force by-products: SUPERSEDES→supersession, CONTRADICTS→contradiction auto-emitted
- numeric_probe.py: extract_claims with qualifier-keyed (unit,qualifier) matching
- Gate stage 5: numeric contradiction probe (log mode default, quarantine mode optional)
- Gate stage 6: L0 echo probe (Jaccard overlap + measured conjunction)
- CONTRADICTS/SUPERSEDES escape valves for numeric probe
- memory:<name> source convention flagged in gate warnings
- Contradiction-aware reflect: pre-synthesis check for CONTRADICTS + numeric contradictions
- Reflect --include-contradictory: min importance, CONTRADICTS edges, inferred basis
- Reflect skip audit: operation=reflect_skip with member names and reasons

### Added (v4 — Unit A)
- Schema v4: `basis` attribute on `<memory:observation>` (measured | inferred | reported)
- `Observation(str)` subclass with basis attribute — zero consumer sweep design
- `serialize_observation` / `deserialize_observation` serializer pair in tags.py
- Neo4j preferred JSON-per-element model for labelled observations
- Basis immutability on upsert; duplicate-text basis upgrade (higher rank upgrades)
- `verified_at` server-managed field — set on measured observations
- `generator_id` config field (env MEMORY_GENERATOR, session-scoped)
- `embed_text` return_model parameter for embed model identification
- V14 validation rule (basis values); Q9 strict warning (unlabelled observations)
- VERIFICATION_RANKS + VALID_BASES constants in config.py
- Basis factor in scoring: measured=1.0, inferred=0.97, reported=0.93 (both backends)
- SUPERSEDES verification guard: source rank ≥ target rank (both backends)
- Staleness presentation: [VERIFIED Nd ago] / [VERIFICATION STALE: Nd] in CLI recall
- `verification_staleness_days` config (default 7)
- `verification_age_hours` in JSON recall output

### Fixed (v4 — Unit A)
- schema.md v3 summary rows: appended R7 to both Schema Versioning and Design Decisions tables
- schema.md: consolidated two overlapping upsert tables into one 16-field table
- technical-reference.md: doctor table completed (added toml_config, rules_inherit, rules_hash)

### Added CLI flags column for all 32 commands with key options
- technical-reference.md: scoring detail — type factor, trust multiplier, BM25 params, weight redistribution, numpy
- technical-reference.md: audit trail section with gate_decision and mutation record schemas
- technical-reference.md: graceful degradation table (Neo4j/Voyage/embedding/concurrent/audit)
- schema.md: trust level hierarchy table with "Can supersede" column
- schema.md: L0 budget enforcement detail (token estimation, eviction, progressive disclosure)
- schema.md: reflect algorithm (6-step clustering → synthesis → SUPERSEDES → archive)
- hierarchy-and-inheritance.md: project auto-derivation from filepath
- README.md: 8-step hook pipeline (write gate, L0 gating, budget enforcement)
- README.md: graceful degradation table
- Status lifecycle semantics — retrieval filtering with `--include-inactive`, traversable-not-returned for superseded entries in BFS recall
- SUPERSEDES trust guard — ingested entries cannot supersede first-party/derived/user entries
- SUPERSEDES cycle detection (R7) — prevents circular SUPERSEDES chains
- `unarchive`, `reactivate`, `release_quarantine` store methods and CLI commands
- `quarantine` CLI command group — list, review, release, reject subcommands
- MEMORY.md line removal on archive status transition
- Provenance immutability — provenance cannot be changed after entity creation
- V13 validation rule — ingested provenance requires `<memory:source>` element
- Untrusted presentation — CLI recall marks ingested entries with `[UNTRUSTED]` delimiter
- Write gate two-verdict pipeline — REJECT (structural) vs QUARANTINE (suspicion) vs ACCEPT
- `gate_pipeline()` function with GateVerdict/GateResult classes
- `log_gate_decision()` audit function for machine-readable gate verdicts
- `quarantine review` CLI command — inspect quarantined entry details
- Type factor in scoring — semantic floor (0.6), episodic standard decay, procedural access-reinforced
- Behavioral specification — On Supersede/Archive/Delete/Quarantine/Mutate lifecycle events
- Upsert immutability table in schema.md
- 32-command CLI reference table in technical-reference.md
- `TRUST_LEVELS` config constant for SUPERSEDES authority guards
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
- Semantic scoring: recency floor at 0.6 (was hard 1.0 — allows some recency signal)
- Procedural scoring: `recency^(1/(1+0.3*access_count))` formula (was `recency^(1-access_count/20)`)
- Neo4j _score_entry: added type factor and trust multiplier (was missing both)
- Neo4j recall: added max_inherit_depth post-filter (was ignoring parameter)
- Neo4j upsert: provenance set only on CREATE, not on MATCH (immutability)
- Neo4j upsert: status and provenance now included in props
- CLI write command: runs write gate pipeline before indexing
- Config neo4j_password default: empty string (was "changeme")
- TOML template: secrets removed, env-only documentation added
- `resolve_rules()` now returns `(effective, overridden)` tuple (single walk)
- Unscoped entities (None/empty project) are universally visible in scoped queries
- Store scoping uses module-level imports instead of repeated inline imports

### Fixed
- Neo4j hub bonus: `min(backlinks, 5)` → `math.log(1 + backlinks)` — scoring parity with JSONL store
- Docker-compose: hardcoded `changeme` password → `${NEO4J_PASSWORD}` env var reference
- Validator R6: dead code cleanup (`level = 'R6' if strict else 'R6'` → `'R6'`)
- Config docstring: "default: changeme" → "no default" (matches actual empty-string default)
- env.example: removed `changeme` placeholder from NEO4J_PASSWORD
- Example scripts: schema="2" → schema="3" in all 3 ingest/consolidation scripts + README
- Doctor count: 20→21 in doctor_cmd, implementation-guide, hierarchy-and-inheritance docs
- Validation coverage: V1-V10→V1-V13, R1-R5→R1-R7 in rules, template, validate_cmd, validator
- schema.md: added V13 and R7 rows to validation rules tables
- Hub bonus formula: `min(backlinks, 5)` → `ln(1 + backlinks)` in rules, template, tech-ref
- Text match scoring: "+0.1" → "+0.1 (Neo4j) or BM25 up to +0.3 (JSONL)" in schema, rules, tech-ref
- Rules file: added type factor to Rule 7, added provenance/status/project to Rule 6 upsert table
- README: added 6 missing CLI commands + 2 hook subcommands
- Schema version: "stays at v2" → "is v3" in hierarchy doc
- Module docstrings: store.py, tags.py, __init__.py updated for v3 features
- Config table: expanded from 9 to 18 fields in technical-reference
- Config precedence: 3 docs said "env vars override everything" — corrected to CLI > env > TOML
- hierarchy-and-inheritance.md Example 4: "env beats CLI" → "CLI beats env and TOML"
- Documentation counts: 432→472 tests, 28→27 files across all docs
- schema="2" → schema="3" in all examples (7 locations across 5 files)
- Stale references: scripts/memory-server/ and ict-neo4j removed
- "Every response" → "Selected responses" in implementation guide
- Optional field count: 8→10 in system overview
- R2 wording: "six defined types" → "six active relation types"
- v3 row added to schema versioning table
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
