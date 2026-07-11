# Memory Entity Schema — Specification (NORMATIVE)

This is the **authority** for what a memory *entity* is: its format, fields, enums, grammars, relations, and
invariants. The harness — the CLI, the validator, the parser, the stores — **conforms to this specification**,
never the other way around. When code and this document disagree about the *entity model or its invariants*,
the code is wrong and adapts up; when they disagree about *implementation mechanics*, see the harness manual
(`harness-manual.md`), which is the reference implementation's operations doc.

The machine source of truth is `src/memoryschema/entity_schema.py`. The **Reference tables** block below is
generated from it by `entity_schema.render_reference_tables()` and diff-checked by
`tests/test_schema_conformance.py`, so it cannot drift from code. Everything else here is the human-readable
normative detail.

## Schema evolution policy

- **Additive-optional fields** (a new frontmatter scalar that older readers can ignore) are added with **no**
  `SCHEMA_VERSION` bump — back-compat is "unknown scalars are ignored on read."
- A **`SCHEMA_VERSION` / format bump** is reserved for a change to the *parse grammar* (a new fence/section
  model, a removed field, an incompatible meaning) — i.e. a change an old reader cannot safely ignore.
- The authority is the single place a field/enum/grammar is defined; the harness imports it. New machinery is
  hung off existing relation types rather than by minting false-precision new ones (see Relations).

## Reference tables (generated — do not hand-edit)

<!-- BEGIN generated: entity_schema.render_reference_tables() -->
- **Entity format:** v5 (current) · v4 XML (legacy, read-only)
- **Types:** `episodic` · `procedural` · `semantic`
- **Statuses:** `active` · `archived` · `quarantined` · `superseded`
- **Relation types:** `CONTRADICTS` · `DEPENDS_ON` · `INFORMS` · `MITIGATES` · `MODIFIES` · `SUPERSEDES` · `USES`  ·  deprecated: `CHILD_OF` · `PARENT_OF`
- **Name / relation-target grammar:** `^[a-z0-9]+(-[a-z0-9]+)*$` (strict kebab-case)
- **Fact-key grammar:** `^[a-z0-9]+(-[a-z0-9]+)*(\.[a-z0-9]+(-[a-z0-9]+)*)+$` (kebab segments joined by dots)
- **Frontmatter fields:** `schema` · `name` · `type` · `status` · `importance` · `project` · `key` · `valid_from` · `superseded_at` · `superseded_by` · `promoted_to` · `relations`
<!-- END generated -->

> Names and relation targets share ONE grammar (strict kebab). Fact **keys** (the temporal `key:` field) are a
> distinct grammar — kebab segments joined by dots (e.g. `memory-schema.multi-space-status`). Parser note
> (Postel): the v5 line parser accepts a *superset* of the target grammar so a legal edge is never dropped on
> parse; the validator enforces the strict grammar. See `entity_schema.py`.

## 1. Format dispatch

Single parse entry point: `tags.parse_memory_content(content, filepath=None)`
(`parse_memory_file` reads UTF-8 and delegates; returns `None` on OS errors).

- If `format_v5.is_v5_content(content)` — the stripped content starts with a `---` fence — the file parses as
  v5 and **never** falls through to XML. (Known edge: `str.lstrip()` does not strip a U+FEFF BOM, so a
  BOM-prefixed v5 file fails dispatch; `parse_v5_content` strips BOM if called directly.)
- Otherwise the v4 XML path runs (§4).
- Write-side selection: `write_index.create_entity_file` emits **v5 by default**; v4 XML authoring is retained
  only for legacy/migration and must be explicitly re-selected (`MEMORYSCHEMA_V4=1` or `MEMORYSCHEMA_V5=0`).
  The chain-file bootstrap always writes a v5 skeleton.

## 2. v5 format (current)

File shape: `---` fence · YAML-subset frontmatter · `---` fence · markdown body.

**Frontmatter grammar** (zero-dependency YAML subset, parsed line-by-line):
- Blank lines and `#`-comment lines skipped.
- `relations:` enters relations mode: each following line matching the relation grammar (see Reference tables)
  appends `{"type", "target"}`; the first non-matching line exits the mode and is parsed as a scalar.
- Scalar lines: `key: value` (not starting with space or `-`); value stripped of surrounding `"` then `'`.
  Unknown keys are ignored.
- The closing fence is the first line whose strip equals `---`. **Unterminated fence → the whole parse returns
  `None`** (a well-formedness failure — see §3).

**Discriminator**: `schema: 5` is REQUIRED. Any other value (or absence) → parse returns `None`, so ordinary
frontmatter markdown (wiki notes) is skipped exactly like non-entity files.

**Recognized frontmatter keys** — the fields in the Reference tables, with rules:

| key | rule |
|-----|------|
| `schema` | must be `5` (discriminator) |
| `name` | from frontmatter if present, else **the filename stem**; neither → `None` |
| `type` | string; default `semantic` |
| `status` | string; default `active` — v5 parse always emits status (the file-first lifecycle carrier) |
| `importance` | int; a non-int value is **silently dropped** |
| `project` | string, kept only if truthy |
| `key` | fact key for temporal validity (e.g. `EURUSD.bias`) (§4.6-temporal, harness manual) |
| `valid_from` / `superseded_at` / `superseded_by` | validity interval + successor (supersession) |
| `promoted_to` | standing-surface marker (e.g. `CLAUDE.md#section`) |
| `relations` | list of `- TYPE target` lines |

**Body grammar**: split on `^## <Title>` headings (exactly two `#`; `###` is content; duplicate headings
merge). The lead precedes the first heading; the **description is the first blank-line-separated paragraph of
the lead** (newlines flattened; later lead paragraphs discarded).

| section | parse |
|---------|-------|
| `## Summary` | prose — the evolving chain summary (replaced by `--desc`) |
| `## Observations` | bullets: `- ` opens an item; following non-bullet non-empty lines join with a space |
| `## Log` | bullets — ordered `Step N: …` entries (chains) |
| `## Reasoning` | prose — appended-to with `\n\n---\n` separators |
| `## Prompt` / `## Chain` | prose — triggering input / chain context |
| `## Notes` | prose → the `body` field |

Unknown `##` sections parse but are **discarded on roundtrip** — do not invent sections. **Nothing in the body
is escaped** — raw `< > &` and even a literal `</memory:entity>` roundtrip verbatim (this is why v5 cannot
suffer the v4 content-corruption class). Roundtrip identity is pinned by `tests/test_format_v5.py`.

## 3. Validation model & the corruption invariant

v5 well-formedness is **parse-based**: `parse_v5_content(...) is None` is the single criterion, and every
deterministic writer re-parses its own output before committing (create refuses to write on failure; append
validates before/after). The content-quality rules (the V/R/Q invariants below) are enforced by the validator.

**Corruption invariant (NORMATIVE):** a *present-but-unparseable* entity file is **corruption, never a
deletion** — `reconcile`/`sync` must surface it and **abort rather than prune** the entity. The guard now
covers v5 as well as v4: `reconcile._parse_md` flags a `---`-fenced file that declares `schema: 5` in its
frontmatter but fails `parse_v5_content`, so a malformed v5 entity aborts the reconcile instead of being
pruned (`_declares_v5_in_frontmatter`, quote-tolerant, frontmatter-scoped).

**Quality invariants (V/R/Q):** structure (V), relations (R — types in the Reference tables, no
self-reference, dedup by (target,type)), filesystem-safe names (F3), and content quality (Q — name is
authority-kebab, description ≤ 120 chars, atomic observations). These now run on **both** formats: `validate()`
format-dispatches — a v5 file is validated by `_validate_v5` (parse-based well-formedness plus the V/R/Q rules
on the parsed entity), a v4 XML file by the legacy path.

## 4. v4 XML format (legacy — parses, not authored)

Read-only legacy. Entity block: first `(<memory:entity\b.*?</memory:entity>)` DOTALL match; text after the
close is `body`. Parsed via stdlib `ElementTree` (namespace prefix stripped). Attributes: `name` (required),
`schema` (default 1), `type`, `status` (carried only when declared), `importance`, `confidence` (v4-only,
retired in v5). Write-side escaping: `&`, `<`, `>` (and `"`). The v4 rule validator (`validator.py`) applies to
v4 files only. **`confidence` is not representable in v5.**

## 5. Relations

The seven active types + two deprecated are in the Reference tables. No self-references; deduped by
(target, type). Each type carries **distinct machinery** (which is why the taxonomy is not collapsed):
- `SUPERSEDES` — flips the target's status to `superseded` (with cycle detection) + L0 removal;
- `CONTRADICTS` — auto-creates the symmetric edge + bypasses the write-gate numeric probe;
- `MITIGATES` — dampens the target's recall score (×0.95), audit-logged;
- `USES` / `INFORMS` — citation-telemetry triggers (attribution).

Three connection types at retrieval: **relations** (authored, forward), **backlinks** (computed reverse),
**associations** (computed embedding k-NN).

## 6. Types & status

`type` is free-form; scoring recognizes `semantic` (recency floor 0.6), `episodic` (standard decay),
`procedural` (access-reinforced recency). `status ∈ {active, superseded, archived, quarantined}`; non-active
entities are excluded from recall/search/L0 by default (`--include-inactive` reveals them); superseded entries
stay graph-traversable.

## 7. Temporal validity & supersession (model)

A fact `key` (e.g. `EURUSD.bias`) plus `valid_from` / `superseded_at` / `superseded_by` gives each fact a
validity interval. **Write-time deterministic supersession:** a `remember --key K` finds the current active
holder of `K` and supersedes it file-first, indexing the new entity *before* retiring the old (so a key is
never left without an active holder). Default recall returns only currently-valid facts; `--as-of <date>`
filters `valid_from <= date < superseded_at`. The write-side adjudication is deterministic (no LLM freshness
judgment). Implementation mechanics live in the harness manual (§4.6).

---

*Harness/operations detail (write pipeline, storage layers, retrieval, telemetry, consolidation, ops, config,
CLI, packaging) is in `harness-manual.md`. This document is the entity-model authority only.*
