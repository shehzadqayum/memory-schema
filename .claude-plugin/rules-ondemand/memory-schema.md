# Memory Schema Reference (v5)

What a valid memory entity looks like, and the write/merge semantics. Loaded on demand —
needed only when hand-authoring or debugging entity files; the deterministic CLI
(`chain step` / `remember`) writes valid entities for you.

**Source of truth:** `packages/memory-schema/docs/schema-specification.md`
(the entity schema — format, fields, enums, grammars, invariants; the write-path *mechanics* live in
`harness-manual.md` §4). This file is a derived quick reference.

---

## The v5 entity (current format)

One markdown file per entity at `memory/<name>.md`. The **name comes from the
filename**. YAML frontmatter carries machine scalars; ALL prose lives in the markdown
body — nothing is ever escaped (raw `<` `>` `&` are safe everywhere).

```markdown
---
schema: 5
type: semantic          # semantic | episodic | procedural (default: semantic)
importance: 7           # 1-10 (default 5; vary it — 7 is the overused mode)
project: helios
key: EURUSD.bias        # optional fact key -> deterministic supersession
valid_from: 2026-07-01  # temporal validity start (auto-stamped with --key)
relations:
  - USES chain-session-2026-07-04
  - SUPERSEDES old-entity-name
---

One-line description, under 120 characters.

## Summary

Evolving summary (chains — replaced by `chain step --desc`).

## Observations

- atomic fact one
- atomic fact two

## Log

- Step 1: chain steps live here, auto-numbered by the CLI

## Reasoning

Narrative: why, alternatives, connections. Appended-to with `---` separators.

## Prompt

The input that triggered this memory.

## Notes

Free markdown (the v4 "body" equivalent).
```

Rules:
- `schema: 5` is REQUIRED (the discriminator — without it the file is ignored).
- Lifecycle fields (`status`, `superseded_at`, `superseded_by`, `promoted_to`) are
  **code-managed** via `set_lifecycle`/CLI — don't hand-author them; they MUST live in
  frontmatter (file-first) or reconcile resurrects the entity.
- Unknown `##` sections are DISCARDED on the next programmatic rewrite — don't invent
  sections.
- Relation lines: `- TYPE target-name`; types: `USES MODIFIES SUPERSEDES DEPENDS_ON
  INFORMS CONTRADICTS MITIGATES`. SUPERSEDES flips the target to superseded;
  CONTRADICTS auto-creates the symmetric edge.
- Validation is parse-based: if `memoryschema sync` reports the file malformed, the
  frontmatter fence or discriminator is broken. (`memoryschema validate` is the v4 XML
  validator — it reports every v5 file as V1; that is expected, not an error.)

## Legacy v4 (parses; do not author)

`<memory:entity schema="4" name="...">` XML blocks still parse and index. XML-escape
`< > &` if you ever must touch one. `set_lifecycle`/`archive` cannot write v4
frontmatter — lifecycle changes on v4 files revert on reconcile (the CLI warns).

## Write & merge semantics

- New names are always writable; existing entities are read-only except the **active
  chain** (`memory/.active_chain`, managed by `chain start/release`).
- Merge on re-index: description/reasoning/status REPLACE; observations APPEND
  (deduped); relations MERGE (deduped by target+type); name/schema/project immutable.
- Write gate: missing name REJECTS; numeric contradictions and L0-echo restatements
  QUARANTINE (review via `memoryschema quarantine list/review/release/reject`).
- Temporal facts: `remember --key X.y` supersedes the previous ACTIVE holder of the key
  deterministically; `recall --as-of ISO-DATE` recalls what was valid then.

## Retrieval scoring (what makes an entity findable)

`score = recency·w_r + importance/10·w_i + relevance·w_v` (semantic weights 0.2/0.3/0.5;
Helios tunes to 0.15/0.15/0.70). Relevance is variance-weighted over 7 embedding spaces
(name, description+summary, observations, prompt, reasoning, chain, default blend).
Type modifiers: semantic floors at 0.6; procedural reinforces with access; episodic
decays. Practical consequences: front-load distinctive wording in the description;
keep observations atomic; link liberally (`--uses`) — backlinks earn a hub bonus and
citations feed attribution.
