# memory-schema — Harness / Operations Manual

**This document specifies the HARNESS** — the reference implementation of the memory system (CLI, hooks,
storage layers, retrieval, telemetry, consolidation, operations, configuration, packaging). The **entity
schema itself** — format, fields, enums, relations, and invariants — is the NORMATIVE authority in
**[`schema-specification.md`](schema-specification.md)**, to which this harness conforms. Written to be
sufficient to rebuild the implementation; the test-suite map in §13 is the rebuild-verification harness.

**Schema version: 5** (YAML frontmatter + markdown body); v4 XML entities remain parse-compatible legacy.
Spec date 2026-07-05 (schema authority split out 2026-07-11). Implementation:
`packages/memory-schema/src/memoryschema/`.

---

## 1. Overview & architecture

A structured, file-first memory system for LLM agents. Every memory is one markdown file
holding one entity. A deterministic write path (CLI commands that accept plain text and
emit structure) is the primary authoring interface; a PostToolUse hook is the safety net
for hand-edited files. Retrieval is embedding-based (multi-space, variance-weighted) with
graph expansion, degrading gracefully to keyword and structural search.

**Core design principles**

1. **Content belongs to the model; structure belongs to code.** The LLM supplies plain
   text; code does escaping, numbering, serialization, and indexing. Hand-authored markup
   corrupted the store twice (the "M14 class": a raw `<`/`&` truncating an XML parse);
   in v5 prose never enters a structured layer, so the class is impossible by construction.
2. **File-first.** The `memory/*.md` set is the content source of truth. Both stores
   (JSONL, Neo4j) are rebuildable projections (`reconcile` rebuilds them *from* the files).
   Consequence: lifecycle state (status, supersession, promotion) MUST live in the file's
   frontmatter — store-only state is resurrected on the next reconcile.
3. **Content-agnostic.** The system does not inspect content for trust; the author
   declares importance, and telemetry (recall log, citation log) measures actual utility.
4. **Never silently drop; degrade loudly.** Every write gets a gate verdict; every
   degradation (Neo4j down, Voyage missing) is a warning or banner, never a silent no-op.
5. **Recall before respond; one chain always active.** The operating protocol (the
   ~534-token kernel injected into every session) drives usage; the machinery here serves it.

**The layers**

| Layer | What | Failure mode |
|-------|------|--------------|
| L0 | `memory/MEMORY.md` — token-budgeted index of active entities | regenerated on every write; never fails |
| L1a | `memory/<name>.md` — one file per entity, git-tracked | source of truth; never fails |
| L1b | `memory/store.jsonl` — JSON-line projection | stdlib-only; rebuildable |
| L2a | Voyage embeddings — 7 spaces × 1024 dims, in `.npz` sidecar | degrades to keyword/structure |
| L2b | Neo4j — graph store, vector + fulltext indexes | degrades to JSONL |

**The loops** (each specified in later sections)

- **Write loop**: `chain step` / `remember` → parse → authorize → embed → gate →
  dual-write (Neo4j AND JSONL) → L0 rebuild → sentinel. (§4)
- **Recall loop**: query → embed → seed scoring → graph cascade → rerank → telemetry. (§6)
- **Consolidation loop** ("the dream pass"): `memoryschema dream` discovers candidates →
  an LLM session judges → safe primitives act (distill/merge/archive/promote). (§8)
- **Health loop**: `preflight` (dependency gate) → `sync` (read-only drift) →
  `reconcile` (heal all layers to the `.md` set). (§9)

---

## 2. On-disk layout

```
<project_root>/
├── memoryschema.toml            # config (project name; optional store/neo4j/voyage/retrieval)
├── .env                         # secrets (VOYAGE_API_KEY, NEO4J_*) — auto-loaded by CLI and hook
├── docker-compose.yml           # Neo4j container (from template)
├── memory/
│   ├── MEMORY.md                # L0 index — REGENERATED, never hand-edited
│   ├── <name>.md                # one entity per file (v5; legacy v4 XML parses)
│   ├── store.jsonl              # L1b projection (no vectors; see sidecar)
│   ├── audit.jsonl              # append-only audit log (§4.7)
│   ├── .active_chain            # single line: the authorized chain name (§4.4)
│   └── .embeddings/             # vector sidecar: <name>.npz per entity (gitignored)
└── .memoryschema/
    ├── recall_log.jsonl         # recall telemetry (§7.1)
    ├── citation_log.jsonl       # citation events (§7.2)
    └── .preflight_ok            # preflight throttle marker (<60s) (§9.1)
```

Path derivation: any entity filepath is normalized (backslashes → `/`); the project root
is everything before the last `/memory/`; `store.jsonl` and `MEMORY.md` are located
relative to that. A file not under a `memory/` directory is refused by the write path.

---

## 3. The entity schema (NORMATIVE) → see schema-specification.md

The entity schema — format, fields, enums, grammars, relations, and the corruption/quality/temporal
invariants — is the NORMATIVE **authority** and lives in its own document:
**[`schema-specification.md`](schema-specification.md)** (generated from `src/memoryschema/entity_schema.py`).
This manual documents the *harness* (the reference implementation) that conforms to it.

## 4. The write path (deterministic)

### 4.1 index_memory — the pipeline

`write_index.index_memory(filepath, config=None, require_active_chain_auth=True)` →
`IndexResult {ok, indexed_to ⊆ [neo4j, jsonl], embedded, warnings, errors, verdict}`.
Expected degradations become warnings; structural failures set `ok=False`.

1. **Normalize**: absolute path, backslashes → `/`; must contain `/memory/`; project
   root = prefix before the last `/memory/`.
2. **Parse** via the dispatch (schema-specification.md); unparseable → error.
3. **Authorize** (when `require_active_chain_auth`): an entity whose name already exists
   in `store.jsonl` is read-only **unless it is the active chain**
   (`memory/.active_chain`). New names always pass. (Supersession re-indexes the old
   holder with authorization off.)
4. **Embed** (degrades, never blocks): with a Voyage key, `embed_all_spaces` fills
   `embedding` (default space), `embeddings` (all spaces), `divergence_profile`, and
   `embed_input_hash` (§6.2). Missing key / API failure → indexed unembedded, warning.
5. **Gate** (§4.5): REJECT → error, nothing written. QUARANTINE → status set to
   `quarantined`, embeddings stripped, indexing continues.
6. **Dual-write**: Neo4j upsert (+ single-entity association recompute) AND JSONL upsert
   (+ backlinks, + associations when embedded). One store failing is a warning; **both**
   failing is the error `both stores failed`. (The hook, by contrast, writes Neo4j OR
   falls back to JSONL — the CLI's dual-write is the deliberate improvement that keeps
   the layers converged write-by-write.)
7. **L0 rebuild** (never blocks): full regenerate of `MEMORY.md` from the surviving
   store's active set under the token budget (§5.4).
8. **Stop-hook sentinel**: best-effort write of the entity name to
   `/tmp/claude-memory-chain-updated` (signals "a memory write happened this response").

### 4.2 chain step — the working-memory writer

```
memoryschema chain step --stdin [--desc "evolving summary"] [--reasoning TEXT] [--uses NAME]...
```

Plain text in (stdin or argument); code does everything else via
`append_chain_step(chain_path, text, desc, reasoning, uses)`:

- **Auto-numbering**: next step = `max(existing "Step N:" numbers, else count) + 1`;
  the prefix `Step N: ` is added unless the text already starts `Step N:`/`Conclusion:`.
- **v5 path**: parse → mutate dict (append to `log`, recompute flattened observations,
  `--desc` replaces `## Summary` — *not* the description, `--reasoning` appends with a
  `\n\n---\n` separator, `--uses` appends deduped USES relations) → serialize →
  **re-parse check before writing** (failure = `ValueError`, file untouched). Multi-line
  step text is collapsed to one line.
- **v4 path** (legacy chains): anchored string surgery before the relevant closing tags,
  all text XML-escaped, then write → re-parse → **rollback on failure**.
- **Bootstrap**: if the active chain's file does not exist, the first step creates a v5
  skeleton (always v5, regardless of the env gate) — `chain start` authorizes the name
  only.
- Then citations are logged for `--uses` (§7.2) and `index_memory` runs.

### 4.3 remember — the durable-fact writer

```
memoryschema remember NAME --desc TEXT --obs TEXT [--obs ...] [--type semantic|episodic|procedural]
    [--importance 1-10] [--reasoning TEXT] [--uses N]... [--informs N]... [--supersedes N]...
    [--key FACT.KEY] [--valid-from ISO] [--body TEXT] [--no-index]
```

Flow: `find_active_by_key` (when `--key`) → `create_entity_file` (refuses to overwrite:
entities are created once; v5 emits `key` + `valid_from` defaulting to today; the v4
branch ignores fact keys and `body` is v4-only) → citation logging for
`--uses`/`--informs` → deterministic supersession of the old key-holder (§4.6) →
`index_memory`.

### 4.4 Chains & authorization

State: `memory/.active_chain` holds one line — the active chain's name.
`chain start <name>` refuses while another chain is active; `chain release` reads and
deletes the file (the same name may be started again later — release is not permanent).
The active chain is the only *existing* entity writable through the content path;
metadata-only mutations via `set_lifecycle` (§4.6) are code-mediated and exempt.
Protocol invariant (kernel): the store never sits without an active chain — conclude,
release, immediately start the successor.

### 4.5 The write gate

`gate_pipeline(memory, store, strict=False, config)` → verdict `ACCEPT | REJECT |
QUARANTINE` + reasons + warnings. Never silently drops.

| stage | condition | outcome |
|-------|-----------|---------|
| validation | missing `name` | REJECT (the only reject) |
| validation | missing description | warning |
| quality nudge | description > 120 chars (non-`chain-` names) | warning |
| quality nudge | importance equals the store mode when the mode covers > 40% of ≥ 10 entries | warning ("vary it") |
| consistency probe | **strict mode only** (not run on the standard path): cosine > 0.95 to a differently-described entry | QUARANTINE |
| numeric probe (stage 5) | needs store + embedding; claims `(value, unit, qualifier)` extracted from description+observations; a ≥ 0.80-cosine neighbour with same unit+qualifier but different value | mode `log` (default): warning; mode `quarantine`: QUARANTINE. Escape valves: hits against declared `CONTRADICTS`/`SUPERSEDES` targets are dropped |
| L0 echo (stage 6) | Jaccard word-overlap ≥ 0.6 between the candidate's description and an existing L0 entry, and no relations beyond the echoed entry | QUARANTINE ("restates X without new content") |

Numeric-probe extraction: `NUM unit [qualifier]` and `unit: NUM` patterns; years and
version tokens skipped; units singularized; stoplist `{percent, version}`. Quarantined
entries are saved with `status=quarantined`, unembedded, for `memoryschema quarantine
list/review/release/reject`.

### 4.6 Temporal validity & lifecycle (file-first)

- **Fact keys**: `remember --key config.timeout` stamps `key` + `valid_from` (default
  today). At write time, `find_active_by_key(store_path, key, exclude=new_name)` finds
  the ACTIVE holder of the same key — exact match, no LLM judgment — and the CLI
  supersedes it: a `SUPERSEDES` relation on the new entity, plus
  `set_lifecycle(old, status="superseded", superseded_at=today, superseded_by=new)`
  and a re-index of the old holder (auth off).
- **set_lifecycle** (v5-only): metadata-only frontmatter mutation — status,
  `superseded_at/by`, `valid_from`, `promoted_to` — with serialize→re-parse check.
  This is the **file-first rule**: because `reconcile` rebuilds the stores *from* the
  `.md` set, lifecycle state living only in a store is resurrected; `archive`,
  `unarchive`, supersession, and promotion all write frontmatter first.
- **Point-in-time recall**: `recall --as-of ISO-DATE` over-fetches (limit×4, min 20,
  inactive included), enriches results with JSONL metadata (recall results are a
  projected subset), and keeps entries with `status ∈ {active, superseded}` whose
  `valid_from (fallback created_at) ≤ as_of < superseded_at (if any)`.
- Both store merge whitelists carry the five lifecycle/temporal fields (`key`,
  `valid_from`, `superseded_at`, `superseded_by`, `promoted_to`) so metadata updates to
  existing entities survive without waiting for a reconcile.

### 4.7 Audit log

`memory/audit.jsonl`, append-only, one JSON event per line, UTC timestamps, 16-hex-char
sha256 value hashes. Event types: mutations (`create | upsert | archive | delete |
status-change`, with per-field prior/new hashes over `description, type, status,
importance, body, prompt, reasoning, project`); `gate_decision` (logged by the legacy
`write` command path); `force` (types `contradiction | supersession | world-change |
decay`, levels `entry | cluster | project`; decay is never eagerly emitted);
`write_decline` (declined write candidates). Audit failures never block mutations.

### 4.8 Citation logging (write-side telemetry)

At the moment `chain step --uses X` or `remember --uses/--informs X` executes, one event
per target is appended to `.memoryschema/citation_log.jsonl`:
`{ts, source, target, context: "chain-step" | "remember"}` — best-effort, never blocks.
This is the utility ground truth joined against recall telemetry in §7.

---

## 5. Storage layers

### 5.1 JSONL store (`store.py: MemoryStore`)

One JSON object per line at `memory/store.jsonl`; whole-file atomic rewrites
(`tempfile` + `os.replace`); mtime-keyed in-process cache; advisory non-blocking
`fcntl` lock on `<path>.lock` around mutations (no-op on Windows — no fcntl; contention
raises "locked by another process").

**Entry fields.** Store-managed: `created_at`, `last_accessed` (UTC ISO), `access_count`
(0), `backlinks` (`{source, type}` — recomputed), `associations` (`{name, score}` k-NN —
recomputed). Content: everything the parser emits (schema-specification.md), observations as plain strings
(legacy `{"text","basis"}` dicts collapse to text on both read and write). Derived:
`embedding` (default space), `embeddings` (per-space), `divergence_profile`,
`embed_input_hash`. On disk only: `vectors_external: true` (§5.3). Absent `status` ≡
`active` everywhere in both stores.

**Upsert.** SUPERSEDES cycles are pre-validated (BFS from the target; a cycle raises
before anything mutates). Insert copies the full dict (all keys persist). Merge:

- replace-if-present whitelist: `type, status, description, importance, body, prompt,
  chain, confidence, key, valid_from, superseded_at, superseded_by, promoted_to,
  embedding, embeddings, divergence_profile`;
- immutable after creation: `name, schema, filepath, project` (also not merged:
  `summary`, `log`, `related`, `embed_input_hash` — see the reconcile note below);
- `reasoning` REPLACES (the `.md` file is the accumulator; appending here doubled chain
  reasoning when the hook re-upserted full text);
- observations append with exact-text dedupe; relations append deduped by (target, type);
- side effects over the merged relation list (targets present in the store only):
  `SUPERSEDES` → target status `superseded` (if active) + audit + force record;
  `CONTRADICTS` → symmetric edge added to the target; `MITIGATES` → audit only.

Known consequence: a merge carrying new vectors does not update `embed_input_hash`
(not whitelisted), so the sidecar skip-if-unchanged can hold a stale vector until
`reconcile` (whose derived-field copy includes the hash) heals it.

**v4/v5 status interaction.** The v4 parser emits `status` only when declared, so
re-indexing a v4 file never overrides store lifecycle. The v5 parser ALWAYS emits status
(default `active`) — re-indexing a v5 file whose frontmatter says active WILL flip a
store-side `superseded/archived` back. This is exactly why lifecycle is file-first
(§4.6): the frontmatter, not the store, is where status lives.

**Lifecycle ops** (all audited): `delete` (removes entry + scrubs inbound
relations/backlinks), `archive` (unconditional), `unarchive` (archived→active only),
`reactivate` (superseded→active only), `release_quarantine` (quarantined→active only),
`access` (the cognitive read: bumps `access_count`/`last_accessed` — recall does NOT).

### 5.2 Neo4j store (`neo4j_store.py`)

Single `:Memory` label; unique constraint on `name`; vector index `memory_embedding`
(1024 dims, cosine) on `m.embedding`; fulltext `memory_fulltext` over name, description,
observations_text, prompt, reasoning; range indexes on type/project/importance/
last_accessed. All DDL idempotent (`schema.py`, declarative `IF NOT EXISTS`, Neo4j 5.11+).

**Upsert**: `MERGE` on name; mutable-prop whitelist applied on CREATE and MATCH:
`schema, type, status, description, importance, body, filepath, prompt, reasoning,
project, key, valid_from, superseded_at, superseded_by, promoted_to`. Observations merge
append-dedupe in Cypher; `observations_text` recomputed. Multi-space vectors as
`emb_<space>` float-array props (absent spaces set null = property removed; a
metadata-only upsert without `embeddings` preserves existing vectors);
`divergence_profile_json` as a JSON string. Relation types are allowlist-validated
before f-string interpolation into Cypher — that allowlist is the injection boundary.
Neo4j does NOT store `chain`, `confidence`, `summary`, `log`, `related`, or
`embed_input_hash`.

**Observable asymmetries vs JSONL** (accepted, documented): SUPERSEDES cycle check runs
after the edge MERGE (auto-committed edge survives the error; JSONL pre-validates);
relations to unknown names MERGE stub target nodes (JSONL keeps the dangling relation,
skips side effects); no audit logging anywhere in the Neo4j store;
`compute_associations` deletes ALL association edges globally before recomputing, even
project-scoped.

**Associations**: `ASSOCIATED_WITH` edges with `score`, top k=10 via the vector index;
`compute_associations_single(name)` (per-write) deletes and recomputes only that node's
edges.

### 5.3 Vector sidecar (`vector_sidecar.py`)

Embeddings live in `memory/.embeddings/<name>.npz` (compressed; keys `hash` =
`embed_input_hash`, `embedding`, `sp_<space>` float32), NOT in `store.jsonl` — entries
on disk carry `vectors_external: true` and are transparently rehydrated on load.
Skip-if-unchanged: the `.npz` is rewritten only when missing/corrupt or its stored hash
differs. Atomic writes; orphan pruning by live-name set (reconcile). Degradations:
no numpy → vectors stay inline (pre-sidecar format); missing/corrupt `.npz` → entry
scored as unembedded, healed by reconcile via the hash. Motivation (measured): 8.41 MB
store for 55 entities was 91.5% vector JSON with ~0.8 s full-file rewrites; externalized
rewrite ~0.7 MB. The sidecar is derived data and gitignored.

### 5.4 L0 index (`l0_budget.py`)

`rebuild_index(index_path, entries|store_path, token_budget, title="## Project Memory")`
is the only writer of `MEMORY.md` (called by the write path, the hook, and reconcile) —
a full REGENERATE, never an append:

- Source: the store's active set; defensive re-filter to active + named.
- Rank: importance DESC (non-int → 5), then name ASC — deterministic and store-agnostic.
- Line: `- [name](name.md) — <description, whitespace-collapsed, truncated to 160 chars>`.
- Grouped: `### Knowledge` (semantic/unknown) · `### Procedures` (procedural) ·
  `### Session History` (episodic).
- Budget: `len(text)//4` estimated tokens; lowest-ranked entries popped until under
  budget (module default 2000; raise via TOML for a large corpus). Truncation is never silent — the
  header note says "N of M active memory entities shown (lowest-importance K dropped)".

Legacy `enforce_budget` (evict-only) and `categorize_index` exist but are no longer the
operative path — the append+evict model could not keep L0 faithful.

---

## 6. Retrieval & embeddings

### 6.1 Embedding client and spaces

- Model: Voyage `voyage-4-lite`, 1024 dims; reranker `rerank-2` (config-overridable).
  `voyageai` is lazy-imported (~1.5 s module cost avoided on non-embedding paths).
- **7 spaces** (`spaces.py` registry): `default, name, description, observations,
  prompt, reasoning, chain` — 1:1 field-to-space plus the default blend. Structurally
  absent fields produce no vector (the combiner skips them). Body text is never embedded.
- `embed_all_spaces` composes every space and embeds them in **one batched call**
  (was 7 sequential round-trips ≈ 2.1 s; batched ≈ 0.25 s).
- **Divergence profile**: at embed time, `1 − cos(space, default)` per non-default space
  (4 dp) — the entry's structural fingerprint and the combiner's weights.

### 6.2 Embedding-input composition (recency-biased) & provenance

`embedding_input.compose_embedding_text(entry, space, max_chars=8000)` is the canonical
composer (`DEFAULT_MAX_CHARS = 8000`; the old 2000-char head-slice is documented in code
as the measured retrieval defect):

- `default`: `name + description + summary` head, then the NEWEST observations that fit
  (tail-first, whole observations, with the first observation prepended as the chain's
  origin anchor when it fits), then prompt + reasoning-tail + chain in remaining budget.
- `observations`: tail-first newest observations. `reasoning`: tail slice (append-only
  narrative — newest after the `---` separators). `name`/`description`(+summary)/
  `prompt`/`chain`: head slices.
- **Provenance**: `embed_input_hash` = sha256 (first 16 hex) of the FULL untruncated
  fixed-order composition (`\x1e`/`\x1f`-joined). Any content change changes the hash
  even when the truncated composed inputs don't — this drives sidecar skip-if-unchanged
  and reconcile's stale-embedding detection.
- v5: `summary` joins the default-space head and shares the description space; log
  entries are part of observations (flattened), so chains embed their newest steps.

### 6.3 Scoring

```
score = recency × w_r + importance/10 × w_i + relevance × w_v      (clamped to 1.0, 4 dp)
```

- **Recency** `0.995^hours_since(last_accessed || created_at)` (missing → 0.5), then
  type modifiers: `semantic` → `max(recency, 0.6)` floor; `procedural` →
  `recency^(1/(1 + 0.3·min(access_count, 10)))` (access-reinforced); `episodic`/unknown →
  standard decay. (The 0.995 literal is hardcoded in the scorers; `config.recency_decay`
  is display/TOML-mappable only.)
- **Importance** `(importance or 5)/10`.
- **Relevance**: per-space `max(0, cos(query, space_vec))` over `entry.embeddings`
  (single `embedding` treated as the default space), combined by the
  **variance-weighted combiner**: `Σ(sim × weight)/Σ(weight)` with default-space weight
  fixed at 1.0 and each field space weighted by its divergence (skipped when ≤ 0); no
  profile → equal-weight mean; single space → pass-through. No base weights, no query
  classification — the data determines the weights.
- **Weights** `(w_r, w_i, w_v)`: `semantic = (0.2, 0.3, 0.5)` (all recall),
  `structured = (0.3, 0.5, 0.2)` (currently uncalled); config-tunable via
  `semantic_weights`/`structured_weights`. No relevance signal → redistribute
  `w_r += 0.4·w_v; w_i += 0.6·w_v; w_v = 0`.
- **Post-sum**: hub bonus `+0.05·ln(1 + backlinks)`; MITIGATES dampening ×0.95 (any
  inbound MITIGATES backlink). `confidence` never enters scoring.
- **BM25 boost** (JSONL seed selection only): k1=1.2, b=0.75, avg_dl=50, no IDF,
  normalized ×0.1 capped at +0.3. Neo4j's lexical equivalent is a +0.1 substring boost
  on seeds — an accepted cross-backend asymmetry.
- numpy batch scoring with pure-Python fallback.

### 6.4 Recall cascade

`recall(query|name, depth=2, decay=0.8, limit, project, include_inactive,
max_inherit_depth=3)` (the CLI never passes depth/decay — `config.recall_depth/decay`
are TOML-mappable but dead in the recall path):

1. **Scope**: `project_matches_scope` — bidirectional (ancestors AND descendants),
   unscoped entities universally visible, depth separation ≤ `max_inherit_depth`.
2. **Returnable** = active only (unless `--include-inactive`); non-active entries stay
   traversable in BFS ("traversable-not-returned" — superseded entries bridge walks).
3. **Seeds**: explicit `name`, else top-3 scored entries (JSONL: full blend + BM25;
   Neo4j: native vector-index search with escalating scoped over-fetch ×3/×9/×100 and a
   +0.1 substring bonus). **Neo4j query-recall returns `[]` without embeddings** (no
   keyword seeding at the store level); JSONL degrades to keyword/recency blend.
4. **BFS** (depth 2, hop decay 0.8): three channels — `relation` (forward) and
   `backlink` (reverse), neighbour score = `hop_score × _score_entry(neighbour)`;
   `association` (k-NN), score = `hop_score × assoc.score` (0.5 default). Max score per
   name wins; better scores re-queue. Neo4j batches each hop's frontier into ONE Cypher
   round-trip, association rows returning scalars only (their vectors never cross bolt —
   ~64% of neighbours are associations, the dominant recall cost).
5. **Rerank** (JSONL path only): when results exceed the limit, the top `limit×3`
   candidates (`"name: description"`) go through Voyage rerank-2; failures keep cascade
   order.
6. Result rows: `{name, score, hop, channel: seed|relation|backlink|association, type,
   importance, description, observations[, relation_type]}` (+ status/project on Neo4j).

`search` is the keyword sibling: substring (JSONL) or Lucene fulltext (Neo4j), filters
only, no scoring/traversal/telemetry. `list` = search with no query, limit 20.
`eval` measures retrieval quality (recall@k, MRR, nDCG over `recall(limit=20)`).

### 6.5 Re-embedding

- `memoryschema embed --prefix P | --all [--space X] [--batch-size 20] [--dry-run]
  [--coverage] [--all-spaces]`: JSONL-direct rewrite (default space, or one space), with
  batch retries (3 attempts, 2s/4s backoff) and post-run association recompute;
  `--all-spaces` runs the full multi-space + divergence backfill through the active
  backend. `--coverage` reports embedded % and multi-space %.
- `reconcile` re-embeds precisely the entries whose `embed_input_hash` no longer matches
  the current file content (§9.3).

---

## 7. Telemetry & attribution

### 7.1 Recall log

Every CLI recall appends one event to `.memoryschema/recall_log.jsonl` (best-effort;
opt-out `MEMORYSCHEMA_RECALL_LOG=0`):

```json
{"ts": "...", "query": "...", "n": 7, "backend": "Neo4jMemoryStore",
 "degraded": false, "hits": [{"name": "...", "score": 0.702, "channel": "seed"}, ...]}
```

`hits` = top 10. `degraded` = backend was not Neo4j. Deliberately separate from scoring —
recall never bumps `access_count`. `memoryschema recall-stats [--strong 0.5]` reports
events, strong-hit rate (top score ≥ threshold), degraded count, recalls/day, top
surfaced, and the never-surfaced set (the dream report's dead-weight feed).

### 7.2 Attribution (recall × citation join)

`memoryschema attribution [--json]` joins the recall log against the citation log
(§4.8): per memory — recalls, citations, `attributed_recalls` (recalls followed by a
citation within `CITE_WINDOW_HOURS = 24`), `attribution_rate`, last recalled/cited.
Summary lists: `recalled_never_cited` (≥ 3 recalls, 0 citations — retrieval noise or
ambient value, reviewed by the dream pass) and `top_attributed` (top 10). The design
point: retrieval telemetry proves memories are FOUND; a citation at the moment
`--uses`/`--informs` executes proves one CHANGED the work. Citations are forward-precise
(logged as they happen); pre-log backlink-era relations are not counted in the rate.

---

## 8. Consolidation — the dream pass

Industry-converged pattern: **code discovers, the LLM judges, safe primitives act.**
Discovery is `memoryschema dream` (read-only, deterministic, no API calls); judgment is
the `/dream-pass` skill session; actions are `remember`/`--supersedes`/`archive`/
`set_lifecycle` — all gated, audited, reversible via git.

### 8.1 The dream report (`dream_report.py`)

Constants: `DUP_COSINE = 0.80` · `STALE_DAYS = 14` · `CHAIN_OBS_ROTATION = 40` ·
`NEVER_SURFACED_GRACE_DAYS = 7`. Reads `store.jsonl` + sidecar rehydration. Seven
candidate sections over ACTIVE entities:

| section | criterion | intended action |
|---------|-----------|-----------------|
| `chains` | `chain-*` name, not the active chain | distill durable lessons into standalone entities, then archive (archive-never-destroy) |
| `oversized` | the active chain with > 40 observations | conclude + release + start a successor |
| `stale_keyed` | has `key` + `valid_from`, ≥ 14 days unrefreshed | re-remember with the same key, or leave if stable |
| `never_surfaced` | zero recall-log appearances; **excluding entities created < 7 days ago** (grace — fresh distillates haven't had a chance) | archive if resolved/expired; reference facts stay |
| `duplicates` | pairwise default-space cosine ≥ 0.80 | merge (`--supersedes` both) or link if distinct |
| `attribution_review` | recalled ≥ 3×, never cited (§7.2) | retrieval noise (archive/refine) vs ambient value (leave, note it) |
| `promotion_candidates` | procedural type OR ≥ 3 citations, no `promoted_to` yet | promote to a standing surface (§8.3) |

Sections needing telemetry are silently empty when the logs are absent. The report never
writes.

### 8.2 The dream session ground rules (the `/dream-pass` skill)

Archive-never-destroy (no `delete`); gated selective evolution (act only on candidates
you can justify — a false merge is worse than a missed one); no content invention
(distillation quotes/compresses what the chain says); distillates carry `--uses <chain>`
provenance; one `Memory(dream):` commit at the end. Cadence: weekly, on ≥ 3 candidates,
or after releasing a large chain.

### 8.3 Skill promotion

A memory that keeps being cited is behaving like a STANDING RULE — recall is the wrong
delivery for it. Promote the distilled instruction into the surface where it belongs
(the kernel for memory-protocol habits, the project CLAUDE.md for operating rules, a
skill for multi-step procedures), then mark it:
`set_lifecycle(memory/<name>.md, promoted_to="<surface>")` + re-index. It drops off the
candidate list but stays recallable with full provenance. Promote at most 1–2 per pass —
a bloated always-loaded kernel is a regression.

### 8.4 Legacy consolidation (`consolidation.py`)

Predates the dream pass; still CLI-wired. `consolidate` backs `memoryschema index`
(bulk parse→upsert of the memory dir, optional default-space embedding of unembedded
entries). `reflect` backs `memoryschema reflect`: clusters ACTIVE episodic entries by
association neighbourhood (score ≥ 0.7, BFS components, size 2–10), skips contradictory
clusters (CONTRADICTS relations or numeric-probe mismatches) unless
`--include-contradictory`, synthesizes a semantic summary entity (Anthropic SDK with a
mechanical join fallback; note: still emits `schema: 4`), SUPERSEDES all members,
archives them.

---

## 9. Operations & health

### 9.1 Preflight — the always-on dependency gate

Fast (sub-second when healthy), distinct from the heavy `doctor`. Chain: **Docker engine
→ Neo4j container (auto-`docker compose up -d` if stopped; Docker Desktop itself is
never auto-started) → bolt probe → schema (vector index present; soft) → Voyage (live
1-token embed)**. Policy: Neo4j hard-required by default (`require_neo4j`, env
`MEMORYSCHEMA_REQUIRE_NEO4J`, default true); Voyage soft by default (degrades to
keyword/BM25) unless `MEMORYSCHEMA_REQUIRE_VOYAGE`.

- `memoryschema preflight [--json] [--no-auto-start] [--require neo4j,voyage]` —
  **exit 1 iff a hard-required dependency failed**; degraded exits 0.
- **Implicit gate**: every CLI invocation runs a banner-only preflight (never
  exits/raises), throttled by the `.memoryschema/.preflight_ok` marker (< 60 s old →
  skip; the marker is written only when fully healthy, so degraded states keep
  re-warning). Escape hatch: `MEMORYSCHEMA_SKIP_PREFLIGHT`.

### 9.2 sync — read-only drift report

`memoryschema sync` diffs the three layers **by name-set** (counts can match while sets
differ): `.md` files vs JSONL vs Neo4j (`list_all(include_inactive=True)`). Reports
malformed files ("reconcile will REFUSE until fixed"), `missing_from_jsonl`,
`jsonl_orphans`, `neo4j_orphans`; Neo4j unreachable reports as `None` — "down" ≠
"empty". Always exit 0.

### 9.3 reconcile — heal all layers to the .md set

Layering contract: **`.md` files are content truth; `store.jsonl` is the materialized
canonical (carries the derived layer); Neo4j is a rebuildable projection.**

`memoryschema reconcile [--dry-run] [--prune/--no-prune] [--no-verify] [--allow-empty]`:

1. Parse the `.md` set. **Malformed guard** (not overridable): any unparseable file that
   declares an entity — `<memory:entity` (v4) or a `schema: 5` frontmatter line (v5, via
   `_declares_v5_in_frontmatter`, which delegates to the parser's own grammar) — aborts the
   run rather than pruning it; a parse failure must never be mistaken for an intentional
   deletion. (Only the unterminated-fence last-wins edge can slip; see §14.)
2. **Shrink/empty guard** (`--allow-empty` bypasses): abort when the `.md` set is empty
   or < 50% of the JSONL count — protects against a misconfigured root wiping the store.
3. Rebuild JSONL to EXACTLY the `.md` set, **reusing the derived layer**
   (`embedding, embeddings, divergence_profile, embed_input_hash, created_at,
   access_count, last_accessed, associations`) whenever the stored `embed_input_hash`
   matches the current content — otherwise re-embed all spaces (Voyage down → entity
   written unembedded, counted in `embed_failed`, never a crash). Atomic write with
   sidecar externalization + orphan pruning.
4. Push to Neo4j (idempotent MERGE import), prune Neo4j names not in the `.md` set
   (re-listed after import so relation-stub nodes are caught), recompute associations
   only when something changed.
5. **Verify by name-set** across all layers (exit 1 on mismatch), then L0 rebuild.

Idempotent: a second run on a clean store is a no-op.

### 9.4 The hooks

**PostToolUse** (`hooks/hook-post-write.sh`; fires on Write AND Edit): the safety net for
hand-edited files. Exit contract: 0 = success or not-a-memory-write; **2 = flag for
Claude review** (stderr feeds back to the agent in the same turn). Pipeline: python
resolution (argv[1] from settings.json → `MEMORYSCHEMA_PYTHON` → PATH probe; missing →
exit 0, never block writes) → path filter (`*/memory/*.md`; MEMORY.md skipped) → sentinel
touch → parse → corruption triage (v4 V9-class parse errors → loud exit 2 with the
"unescaped `<`/`&`" hint; a corrupt **v5** file exits 0 silently — v5 safety is the
writers' round-trip checks) → active-chain authorization (blocked = indexing skipped,
exit 0; the file write itself is not reverted) → embed (before the gate — stages 5–6
need the vector) → gate (REJECT → exit 2; QUARANTINE → saved unembedded) → **Neo4j-first
index with JSONL fallback** (both fail → exit 2) → L0 rebuild from the store just
written.

Local patches carried in the hook script (package source — `hook upgrade` edits only
`settings.json`, never the script): (1) Windows backslash normalization
(`FILE_PATH="${FILE_PATH//\\//}"`) so the `/memory/` match works on Windows paths;
(2) project `.env` autoload (root = path prefix before `/memory/`; safe line parser,
values never eval'd) so the hook has DB/API credentials in any shell.

**Stop hook** (`hooks/hook-stop.sh`; always exit 0): if an active chain exists and the
sentinel was NOT touched this response, emits
`{"systemMessage": "MEMORY CHAIN REMINDER: ..."}` (Stop hooks support only top-level
`systemMessage`; the PostToolUse hook uses `hookSpecificOutput` — these are the two hook
output formats). Sentinel present → consumed silently.

### 9.5 Neo4j container lifecycle

`memoryschema neo4j deploy` (pull → up → healthcheck poll 60 s → schema → verify) ·
`up` / `down` (docker compose) · `status [--json]` · `logs [--tail 50]` · `schema`
(idempotent DDL) · `reset --confirm` (DETACH DELETE all + recreate schema) · `shell`
(cypher-shell exec). Container name = `{project_name}-neo4j`. Docker binary discovered
via PATH + common locations; a dead engine exits 1 with diagnostics.

---

## 10. Configuration

### 10.1 Resolution order (highest → lowest)

1. CLI flags (`--project`, `--root`)
2. Env vars: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `VOYAGE_API_KEY`,
   `MEMORY_PROJECT`
3. Parent `memoryschema.toml` (parent wins on conflict — walked up to 20 directories)
4. Child `memoryschema.toml`
5. Dataclass defaults

`.env` autoload: every CLI invocation loads the nearest `.env` walking up from `--root`
(python-dotenv or a minimal fallback parser; never overrides already-set vars); the
PostToolUse hook does the same from the written file's project root. Secrets belong in
`.env`, never TOML.

### 10.2 MemoryConfig defaults (exact)

| field | default | notes |
|-------|---------|-------|
| `project_name` / `project_root` | `default` / CWD | container name `{project}-neo4j` |
| `store_path` | `<root>/memory/store.jsonl` | |
| `neo4j_uri` / `user` / `password` | `bolt://localhost:7687` / `neo4j` / `""` | env-overridable |
| `embed_model` / `embed_dimensions` | `voyage-4-lite` / 1024 | |
| `rerank_model` | `rerank-2` | |
| `require_neo4j` | **true** | env `MEMORYSCHEMA_REQUIRE_NEO4J`; gates preflight + index/write/import |
| `require_voyage` | false | env `MEMORYSCHEMA_REQUIRE_VOYAGE` |
| `l0_token_budget` | **2000** (raise via TOML for a large active corpus) | TOML `retrieval.l0_token_budget` |
| `recency_decay` | 0.995 | display/TOML only — scorers hardcode 0.995 |
| `association_k` | 10 | |
| `recall_depth` / `recall_decay` | 2 / 0.8 | TOML-mappable but the CLI never passes them — store defaults rule |
| `max_inherit_depth` | 3 | hierarchy depth separation cap in recall |
| `verification_staleness_days` | 7 | recall staleness annotation |
| `mitigation_dampening` | 0.95 | (scorers hardcode the literal) |
| `semantic_weights` / `structured_weights` | (0.2, 0.3, 0.5) / (0.3, 0.5, 0.2) | TOML-tunable |
| `numeric_probe_enabled` / `mode` / `sim_threshold` | true / `log` / 0.80 | gate stage 5 |
| `l0_echo_threshold` | 0.6 | gate stage 6 |
| `generator_id` | None | env `MEMORY_GENERATOR` (session-scoped) |

Canonical constant sets are defined in `entity_schema.py` (the single authority) and re-exported by
`config.py`: `VALID_TYPES`, `VALID_STATUSES`, `VALID_RELATION_TYPES` + `DEPRECATED_RELATION_TYPES`,
`SCHEMA_VERSION = 5` (tracks the current entity format). The legacy v4-XML `schema=` attribute ceiling is the
separate constant `V4_XML_SCHEMA_VERSION = 4`, used only by the validator's V10 range check.

### 10.3 Example deployment config (`memoryschema.toml`)

```toml
[project]
name = "my-project"                      # env MEMORY_PROJECT wins
[retrieval]
semantic_weights = [0.2, 0.3, 0.5]       # default; tune relevance-heavy (e.g. [0.15, 0.15, 0.70]) for a
                                         # recall-driven corpus
l0_token_budget = 2000                   # raise (e.g. 3000) for a large active corpus
```

### 10.4 Project hierarchy & inheritance

Dot-notation project names (`parent.child.grandchild`, kebab-case segments). Two
matching modes: `project_matches_scope` (recall — bidirectional ancestor/descendant,
depth separation ≤ `max_inherit_depth`) and `project_matches_filter` (search/list —
subtree only). Unscoped entities are universally visible in both. Config TOMLs and
`.claude/rules/` inherit upward with parent-wins-on-conflict; child-unique keys/rules
are additive. Inspect with `memoryschema config --chain` and `memoryschema rules
--conflicts`. Deep-dive: `docs/hierarchy-and-inheritance.md` (non-normative satellite).

---

## 11. CLI reference (complete)

Entry point: `memoryschema` (`cli/main.py:cli`, console script). Group options
**precede** the subcommand: `--project NAME` (env `MEMORY_PROJECT`, default `default`),
`--root PATH` (env `MEMORY_ROOT`, default `.`). Every invocation: `.env` autoload →
config resolution → throttled banner-only preflight (§9.1). `--json` on query commands;
`--confirm` on destructive commands. Exit codes: 0 success, 1 command failure, 2 usage.

**Write path (primary)**

| command | behavior |
|---------|----------|
| `remember NAME --desc --obs... [--type] [--importance] [--reasoning] [--uses]* [--informs]* [--supersedes]* [--key] [--valid-from] [--body] [--no-index]` | §4.3; keyed supersession; citation logging; dual-write index |
| `chain status / start NAME / release` | §4.4 (start authorizes the name only; step bootstraps the file) |
| `chain step [TEXT] [--stdin] [--desc] [--reasoning] [--uses]* [--no-index]` | §4.2 |
| `force --type world-change\|contradiction\|supersession --target NAME [--level]` | typed audit force record |
| `decline --reason TEXT [--name-hint]` | write-decline audit record |

**Query**

| command | behavior |
|---------|----------|
| `status [--json]` | backend, node count, store path, URI |
| `recall QUERY [-n 10] [-p PROJECT] [--include-inactive] [--as-of ISO] [--json]` | §6.4 + telemetry; `--as-of` = point-in-time (§4.6) |
| `recall-stats [--strong 0.5] [--json]` | telemetry stats (§7.1) |
| `attribution [--json]` | recall × citation join (§7.2) |
| `dream [--json]` | consolidation candidate report (§8.1), read-only |
| `get NAME [--json]` / `list [--type] [--project] [-n 20] [--include-inactive]` / `search TEXT [...]` | single entity / filtered list / keyword search |
| `eval [--mode retrieval\|salience\|ablation\|backends] [--store PATH] [--json]` | retrieval-quality metrics (recall@k, MRR, nDCG) |

**Lifecycle & review**

| command | behavior |
|---------|----------|
| `archive NAME` / `unarchive NAME` / `reactivate NAME` | status transitions; archive/unarchive are file-first via `set_lifecycle` (v4 files warn "will revert on reconcile") |
| `quarantine list / review NAME / release NAME / reject NAME --confirm` | gate-quarantine review workflow |
| `delete NAME --confirm` | removes store entry + `.md` + MEMORY.md line + inbound references |

**Maintenance & health**

| command | behavior |
|---------|----------|
| `preflight [--json] [--no-auto-start] [--require csv]` | §9.1; exit 1 on hard failure |
| `sync` | §9.2 read-only name-set drift |
| `reconcile [--dry-run] [--prune/--no-prune] [--no-verify] [--allow-empty]` | §9.3; exit 1 on abort/verify-fail |
| `doctor [--json] [--fix]` | 22 live checks (python→tests); `--fix` prints fix commands, advisory only; always exit 0 |
| `validate [PATH] [--strict] [--json]` | rule validator; format-dispatched — v5 via `_validate_v5`, v4 XML via the legacy path (an unparseable `schema: 5` file reports a single V1). schema-specification.md |
| `index [--base-path] [--project] [--embed]` | bulk consolidate (hard-requires Neo4j) |
| `embed [--prefix\|--all] [--space X] [--all-spaces] [--coverage] [--batch-size 20] [--dry-run]` | §6.5 |
| `associations [--recompute] [--k 10]` | k-NN edge stats/recompute |
| `reflect [-p] [--min-cluster 2] [--max-cluster 10] [--score-threshold 0.7] [--dry-run] [--include-contradictory]` | §8.4 episodic→semantic |
| `migrate jsonl-to-neo4j [--batch-size 500] [--dry-run] [--verify] [--skip-assoc]` / `migrate neo4j-to-jsonl [--output]` | store-to-store migration (idempotent MERGE / full mirror export) |
| `write FILE` | legacy: parse+validate+gate+embed(default-space)+index — effectively v4-only (schema-specification.md); hard-requires Neo4j |

**Infrastructure**

| command | behavior |
|---------|----------|
| `init [--with-neo4j] [--scopes working,corpus] [--neo4j-password]` | scaffolds memory/, MEMORY.md, docker-compose.yml, .env.example, memoryschema.toml, rules templates (never overwrites) |
| `neo4j deploy / up / down / status / logs [--tail 50] / schema / reset --confirm / shell` | §9.5 |
| `voyage status / test TEXT` | key check + live embed probe |
| `hook install [--per-project] / uninstall / status / upgrade [--dry-run] / check / scan / test FILE` | hook management; HOOK_VERSION=2 = Write\|Edit matcher + Stop hook; timeouts 10 s / 5 s. `upgrade` edits `settings.json` only, never the hook script (§9.4) |
| `plugin deploy [--force] / uninstall [--confirm] [--keep-data] / status` | deploys skills/rules to `~/.claude/` with a manifest |
| `backup [--output] [--jsonl-only\|--files-only]` / `restore ARCHIVE --confirm` / `export [--format tar\|jsonl\|md]` / `import SOURCE` / `reset --confirm [...]` / `clean [--confirm] [--dry-run]` | archival & teardown; `import` jsonl/md hard-requires Neo4j |
| `config [--json] [--chain]` / `rules [--json] [--conflicts]` | resolved config / rules inheritance inspection |

Environment variables (complete): `MEMORY_PROJECT`, `MEMORY_ROOT`, `MEMORY_GENERATOR`,
`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `VOYAGE_API_KEY`, `MEMORYSCHEMA_V5` / `MEMORYSCHEMA_V4`
(legacy-v4 opt-out — v5 is the authored default; set `MEMORYSCHEMA_V4=1` or `MEMORYSCHEMA_V5=0` to author v4
XML), `MEMORYSCHEMA_REQUIRE_NEO4J` (default true),
`MEMORYSCHEMA_REQUIRE_VOYAGE` (default false), `MEMORYSCHEMA_SKIP_PREFLIGHT`,
`MEMORYSCHEMA_RECALL_LOG=0` (telemetry opt-out), `MEMORYSCHEMA_PYTHON` (hook
interpreter), `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` (required on Windows cp1252
consoles).

---

## 12. Packaging & dependencies

- Package `memory-schema` 0.1.0 (version dual-maintained in `pyproject.toml` AND
  `_version.py` — keep in sync). src-layout; Python ≥ 3.11 (stdlib `tomllib`); MIT.
  Package data ships `templates/*` and `hooks/*`. Console script:
  `memoryschema = memoryschema.cli.main:cli`.
- Required dependency: `click>=8.0` only. Extras: `[neo4j]` neo4j≥5.0, `[embeddings]`
  voyageai≥0.3 (lazy-imported), `[numpy]` numpy≥1.24 (pure-Python fallbacks
  everywhere), `[all]`, `[dev]` pytest + cov/mock/timeout.
- **Vendoring:** a host project can vendor this package (e.g. at `packages/memory-schema`, installed editable
  into the project venv) instead of consuming it from PyPI — the vendored copy is then the canonical source,
  and any local modifications are ordinary committed code (there is no upstream to re-sync from). The
  deployable `.claude/` artefacts ship as package-data under `claude_plugin/`, so `plugin sync`/`init` work
  from any install.
- Public API: eager exports (MemoryConfig, MemoryStore, get_store, parsers, validators,
  consolidate/reflect, hierarchy/inheritance helpers) + PEP 562 lazy exports
  (`Neo4jMemoryStore`, `embed_text/embed_batch/rerank`, the `embeddings` submodule).

### 12.1 Operational artefacts (skills & rules) — the single source of truth

The runnable operating system (the skill(s) + the injected rules) is versioned IN the
package at **`packages/memory-schema/src/memoryschema/claude_plugin/`** — not just described in this spec
— so a deployment can be reconstructed and the package never drifts from what actually
runs. `memoryschema plugin deploy` installs these into `~/.claude/`; the manifest at
`~/.claude/memory-schema-manifest.json` records exactly what was placed, and `plugin
status`/`uninstall` read it.

| artefact (`src/memoryschema/claude_plugin/…`) | deploys to | role |
|-------------------------------|-----------|------|
| `skills/dream-pass/SKILL.md` | `~/.claude/skills/dream-pass/` | the consolidation procedure (§8.2) |
| `rules/memory-working.md` | `~/.claude/rules/` | the always-loaded ~534-token protocol kernel (§1 principle 5) |
| `rules-ondemand/memory-schema.md` | `~/.claude/rules-ondemand/` | the v5 authoring reference (schema-specification.md), loaded on demand |
| `rules-ondemand/memory-corpus.md` | `~/.claude/rules-ondemand/` | corpus-ingestion guidelines (deploy with `init --scopes corpus`) |

`SKILL_FILES`/`RULE_FILES` in `cli/plugin_cmd.py` MUST stay in sync with that directory.
Separately, `src/memoryschema/templates/*.tpl` are the GENERIC scaffolds `init` writes
into a fresh project (the `src/memoryschema/claude_plugin/` copies are the deployed, possibly-tuned
operational versions — edit those, then re-deploy; do not hand-maintain divergent copies
in a project's `.claude/`).

**Mechanical, MD5-verified sync.** `memoryschema plugin sync` deploys the canonical
artefacts into a project's `.claude/` (default `<project_root>/.claude`; `--global` targets
`~/.claude`) as a **verifiable derived copy**: it MD5s each source against its deployed
copy and writes only the files that are missing or differ. `plugin sync --check` is
read-only — it reports drift and **exits non-zero** (a CI / pre-commit / session-start
gate) without writing. A deployment may run `plugin sync --check` at session start (e.g. via a
session-start hook / bootstrap script) and warn on drift, so it never silently diverges from the
package source of truth.

The session-start hook is **advisory** by decision (2026-07-07): it detects-and-warns,
never overwrites, so a session start cannot silently revert a file mid-edit. It MAY become
**auto-repair** later (the deployment always mirrors the package) once `.claude/` is
treated purely as a build output — the flip is dropping `--check` from the hook line.

**Package-source vs. deployment-local.** Machine/ops-specific artefacts are deliberately
NOT in the package (they carry absolute paths or non-portable ops): a deployment's SessionStart
hook, its ops/bootstrap scripts (dependency auto-start), and its tuned `memoryschema.toml`. Those
live in the deployment repo, by design.

---

## 13. Test suite — the rebuild-verification map

~872 tests across 56 files. Hermetic by construction: `tests/conftest.py` strips all
live env per test, points `NEO4J_URI` at a guaranteed-dead endpoint, sets
`MEMORYSCHEMA_SKIP_PREFLIGHT=1` and `MEMORYSCHEMA_RECALL_LOG=0`, and runs a
session-scoped **live-Neo4j wipe tripwire** (snapshots the live node count when real
credentials are present; a drop at session end prints a loud banner — motivated by the
2026-07-04 incident where a test-isolation leak silently wiped the live store).
Invocation: `cd packages/memory-schema && python -m pytest tests/` (env-free;
integration tests deselected by default, `-m integration` opts in; 30 s thread-method
timeout for Windows).

Coverage map (file → what it pins): `test_format_v5` (v5 grammar, M14 acid),
`test_write_index` (deterministic write path), `test_temporal_validity` (keys,
--as-of, file-first), `test_attribution` (+ promotion machinery + store lifecycle-merge
whitelist), `test_dream_report`, `test_vector_sidecar`, `test_embedding_input_recency`
(recency composition + provenance hash), `test_store` (67 — JSONL core),
`test_neo4j_store` + `test_recall_bfs` (batched BFS), `test_field_spaces` (52 —
multi-space scoring), `test_hierarchy` (84) + `test_inheritance` (56), `test_write_gate`
+ `test_numeric_probe`, `test_l0_budget` + `test_l0_rebuild`, `test_reconcile` +
`test_cli_memschema` (guards), `test_get_store_degrade` + `test_preflight` (loud
degradation), `test_status_supersession_fix` (v4 status non-reversion),
`test_schema_idempotent` (vector-index DDL), CLI files per command group, `eval/`
(fixtures + recall@k/MRR/nDCG harness). Full listing: the tests/ directory is
self-describing; treat the suite, not the CHANGELOG, as the authoritative behavior
record.

---

## 14. Known asymmetries, quirks & invariants (accepted and documented)

**Invariants (violating any of these is a bug):**

1. Prose never enters a structured layer on the v5 write path (M14 impossible).
2. Every deterministic writer re-parses its own output before/after committing
   (refuse-to-write or rollback).
3. Lifecycle state lives in `.md` frontmatter (file-first) — never store-only.
4. `reconcile` is idempotent and never destroys: malformed guard, shrink guard,
   archive-never-delete on the consolidation loop.
5. The CLI write path dual-writes both stores; a recall never mutates scoring state
   (`access_count` untouched); telemetry is append-only and best-effort.
6. Degradation is loud (banners/warnings), never silent.

**Accepted asymmetries / quirks (documented so a rebuild doesn't "fix" them blindly):**

- Neo4j query-recall returns `[]` without embeddings (JSONL degrades to keyword);
  JSONL has BM25 (+0.3 cap), Neo4j has substring +0.1; rerank exists on the JSONL
  path only.
- SUPERSEDES cycles: JSONL pre-validates; Neo4j detects after the auto-committed edge
  MERGE. Neo4j MERGEs stub nodes for unknown relation targets; JSONL skips side
  effects. The Neo4j store performs no audit logging.
- JSONL merge doesn't update `embed_input_hash` (stale until reconcile); Neo4j stores
  no `chain/confidence/summary/log/related/embed_input_hash` at all.
- `hook install --timeout` changes only the echoed message (registered timeout is the
  constant 10 s). `backup --neo4j-only` falls through to a full backup. `validate`
  `--json` mode exits 0 even with errors. `doctor` always exits 0; its docstring still
  says "21-point" (22 checks). `config.recency_decay`/`mitigation_dampening`/
  `recall_depth`/`recall_decay` exist as config fields but the operative values are
  hardcoded at their call sites.
- A corrupt v5 file is silently skipped by the hook, but the reconcile malformed-guard now
  detects it (via its `schema: 5` frontmatter declaration) and refuses to prune its entity —
  v5 safety also lives in the writers' round-trip checks (schema-specification.md).
- `remember --body` survives only on the v4 branch; fact keys survive only on v5.
- The chain bootstrap always writes v5 regardless of `MEMORYSCHEMA_V5`.

---

*This specification supersedes `docs/schema.md`, `docs/technical-reference.md`,
`docs/implementation-guide.md`, and `docs/system-overview.md` (deleted 2026-07-05; see
git history). Satellites: `docs/hierarchy-and-inheritance.md` (feature deep-dive),
`docs/design/` and `docs/plans/` (historical design records), `docs/reports/`
(historical session reports). The LLM-facing quick reference derives from this spec at
`.claude/rules-ondemand/memory-schema.md`.*
