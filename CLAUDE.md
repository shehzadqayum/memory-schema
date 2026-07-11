# memory-schema — package guide (for a session working INSIDE this package)

An LLM memory system: v5 entity files (`memory/*.md`) → JSONL store → Neo4j + Voyage embeddings, with a
deterministic write path, a PostToolUse indexing hook, and a CLI. In Helios this is **vendored** at
`packages/memory-schema/` and installed editable into `helios\.venv`. On extraction it becomes a standalone
private repo (this file travels with it as the repo's CLAUDE.md).

**This vendored copy IS the canonical source** — there is no upstream to sync from, so historical "re-apply on
re-vendor" local patches (7-space activation, hermetic-test isolation, the Neo4j fixes, the three hook patches)
are simply committed code now. **No `memoryschema` command regenerates the hook script** — `hook upgrade` only
edits `~/.claude/settings.json` (the tool matcher + Stop registration), never the script — so the patches are
safe unless you replace the package files.

## The doctrine: the schema is the authority, the code is its harness

- `src/memoryschema/entity_schema.py` is the **single machine authority** for the entity model — fields,
  enums, the name/target grammar (`NAME_RE`), the fact-key grammar (`KEY_RE`), `SCHEMA_VERSION`. The harness
  (`config.py`, `validator.py`, `format_v5.py`) **imports** these; it never re-declares them.
- `docs/schema-specification.md` is the **NORMATIVE prose authority** (format, invariants, corruption rule,
  temporal validity). `docs/harness-manual.md` is the **ops/mechanics manual**. When code and the schema spec
  disagree about the *entity model*, the **code adapts up**; when they disagree about *mechanics*, the manual
  syncs down.
- The `## Reference tables` block in `schema-specification.md` is **generated** by
  `entity_schema.render_reference_tables()` and diff-checked by `tests/test_schema_conformance.py` — so the
  machine-readable doc sections cannot drift from code.

## Dev workflow

- **Tests are hermetic** — run env-free (no live Neo4j/Voyage): `cd packages/memory-schema && python -m pytest
  tests/`. ~930 pass; `-m integration` is the live-Neo4j class, excluded by default. `conftest.py` strips
  ambient backend env so a developer shell with `.env` loaded stays isolated.
- `tests/test_schema_conformance.py` is the **anti-drift gate** — it asserts the harness single-sources the
  grammar and that validator + parser agree with the authority. Keep it green; add an xfail→pass when a
  harness gap is closed.
- `.claude-plugin/` is the **SSOT for deployed rules/skills**; deploy with `memoryschema plugin sync`
  (`--check` is a CI/session-start drift gate). Editing the deployed `.claude/` copy directly drifts.
- Keep `CHANGELOG.md` `[Unreleased]` current — the audit found it drifts; bake the habit in.
- Always `export PYTHONUTF8=1 PYTHONIOENCODING=utf-8` before any CLI call (Windows cp1252 crashes on Unicode).

## Hard constraints (lessons paid for)

- **Never bulk find-replace across the schema/harness split.** Route schema-refs vs harness-refs by hand — a
  blunt filename replace recurred as a defect class three times (it can't tell which authority a `§3` points at).
- **Guard/validator logic DELEGATES to the parser, never re-implements the grammar.** The corruption guard
  (`reconcile._declares_v5_in_frontmatter`) and validator scans call `format_v5._parse_frontmatter` /
  `parse_v5_content`'s discriminator. A hand-rolled parallel scan diverged (quoted / spaced-colon / indented
  `schema:`) three times — each a silent-prune data-loss risk. Parse-liberally / validate-strictly (Postel):
  `format_v5._REL_RE` is a documented **superset** of `NAME_RE`; the validator enforces the strict grammar.
- **v5 is the authored default.** `create_entity_file` emits v5; v4 XML authoring is legacy, reachable only via
  `MEMORYSCHEMA_V4=1` / `MEMORYSCHEMA_V5=0`. v4 files still parse (read + migration).

## Security posture

- The hook `src/memoryschema/hooks/hook-post-write.sh` carries **THREE local patches** (package source — no CLI
  regenerates it): (1) Windows backslash-path normalization, (2) `.env` autoload, (3) **`.env`-export
  allowlist** — it exports only `NEO4J_*` / `VOYAGE_*` / `MEMORYSCHEMA_*` / `MEMORY_*`, never the whole `.env`
  (the HIGH-2 fix).
- `preflight._start_container` prefers `docker start` (runs no file) and only `compose up`s a file carrying the
  `memoryschema-managed` sentinel — an **anti-footgun, not an adversarial boundary** (the token is copyable).
- The generated compose references `${NEO4J_PASSWORD}` (secret in the gitignored `.env`, never baked at rest).

## Accepted limitations (documented, not bugs)

- The corruption guard can miss an *unterminated-fence* file whose body later carries a column-0
  `schema: <non-5>` (parser last-wins). Detecting intent inside a corrupt file is inherently ambiguous;
  matching the parser exactly beats a heuristic that mis-flags valid notes.

## Status

Schema split complete (authority + harness conformance B1–B4 + security). **Extraction** to a standalone
private repo (git-subtree → `main` + a `deployments/helios` pointer branch) is the next step, not yet started.
