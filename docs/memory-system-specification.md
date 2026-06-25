# Memory System Specification

**Version:** Schema v4
**Architecture:** Content-agnostic, 7-space embedding, variance-weighted retrieval
**Date:** 15 June 2026

---

## 1. Overview

A structured memory system for LLM agents. Every memory is an XML entity stored as a markdown file. A PostToolUse hook automatically parses, embeds, gate-checks, and indexes entities on write. Retrieval uses a variance-weighted multi-space combiner to rank entries by semantic relevance, recency, and importance.

The system is **content-agnostic** — it does not inspect content for trust signals. The author declares importance and confidence; the system stores and retrieves without judgment.

---

## 2. Entity Schema

### 2.1 XML Structure

```xml
<memory:entity schema="4" name="unique-name" type="knowledge" importance="7" confidence="8">
  <memory:description>One-line summary (under 120 chars)</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact 1</memory:observation>
    <memory:observation>Atomic fact 2</memory:observation>
  </memory:observations>
  <memory:prompt>The user input that triggered this memory</memory:prompt>
  <memory:reasoning>Why this approach, what alternatives, what connections</memory:reasoning>
  <memory:chain>What investigation or reasoning sequence this belongs to</memory:chain>
  <memory:relations>
    <memory:relation target="other-memory" type="USES"/>
  </memory:relations>
  <memory:project>project-name</memory:project>
</memory:entity>

Optional body text (markdown) after the closing tag.
```

### 2.2 Fields

#### LLM-Authored (13 fields)

| Field | Location | Required | Upsert Behavior | Embedding Space |
|-------|----------|----------|-----------------|-----------------|
| `schema` | attribute | **Yes** | Immutable | — |
| `name` | attribute | **Yes** | Immutable | **name** |
| `description` | child element | **Yes** | Replaced | **description** |
| `importance` | attribute | No (default 5) | Replaced | — |
| `confidence` | attribute | No (V12: 1-10) | Replaced | — |
| `type` | attribute | No (free-form) | Replaced | — |
| `observations` | child element | No | Appended (deduped) | **observations** |
| `prompt` | child element | No | Replaced | **prompt** |
| `reasoning` | child element | No | Replaced | **reasoning** |
| `chain` | child element | No | Replaced | **chain** |
| `relations` | child element | No | Merged (deduped) | — |
| `project` | child element | No | Immutable | — |
| `body` | after closing tag | No | Replaced | — |

#### System-Managed (9 fields)

| Field | Purpose |
|-------|---------|
| `status` | `active` / `superseded` / `archived` / `quarantined` — set by lifecycle events |
| `embedding` | Legacy single vector (= default space) |
| `embeddings` | Dict of 7 space vectors |
| `divergence_profile` | Per-space cosine distance from default — structural fingerprint |
| `created_at` | ISO 8601 timestamp, set once |
| `last_accessed` | Updated on every recall access |
| `access_count` | Incremented on every recall access |
| `backlinks` | Reverse relations, computed from other entries' relations |
| `associations` | k-NN neighbors, computed from embedding similarity |

#### Special Fields

- **`confidence`** is write-time metadata only. It does NOT affect retrieval scoring. Captured immutably for calibration analysis (checking declared confidence against downstream entry fate). V12 validates range 1-10.
- **`type`** is free-form. The scoring engine recognises `semantic`, `episodic`, `procedural` for recency modifiers (see §4.3), but any string is accepted. The validator does not restrict type values.
- **`importance`** defaults to 5 when omitted. Used directly in scoring: `importance/10 × w_i`.

### 2.3 File Format

- **Filename:** `<name>.md` — must match the `name` attribute exactly
- **Path:** `memory/<name>.md`
- **Encoding:** XML-escape `<`, `>`, `&`, `"`. Unicode supported.
- **Body:** Optional markdown text after `</memory:entity>`

---

## 3. Write Pipeline

```
User writes memory/*.md
    │
    ▼
┌─────────────┐     Not <memory:entity>?
│ PostToolUse  ├──────────────────────────▶ exit 0 (skip silently)
│ Hook fires   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│ AUTHORISATION CHECK                              │
│                                                   │
│ Name exists in store?                            │
│   NO  → allowed (new memory)                     │
│   YES → name == memory/.active_chain?            │
│           YES → allowed (authorised chain upsert)│
│           NO  → blocked (read-only)              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ EMBED — 7 spaces × 1024 dims (Voyage AI)         │
│                                                   │
│ For each space (default, name, description,      │
│ observations, prompt, reasoning, chain):          │
│   1. Compose text via compose_embedding_text()   │
│   2. If text is empty → skip (structural absence)│
│   3. Embed via Voyage AI voyage-4-lite           │
│   4. Store vector in entry['embeddings'][space]  │
│                                                   │
│ DIVERGENCE PROFILE                               │
│ For each field space:                            │
│   div[space] = 1.0 - cosine_sim(field, default)  │
│ Stored as entry['divergence_profile']            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ GATE PIPELINE — 4 stages, 3 verdicts             │
│                                                   │
│ Stage 1: VALIDATION                              │
│   name required → REJECT if missing              │
│   description expected → warning if missing      │
│                                                   │
│ Stage 2: CONSISTENCY                             │
│   >0.95 cosine sim with existing entry           │
│   + different description → QUARANTINE           │
│                                                   │
│ Stage 3: NUMERIC PROBE                           │
│   extract_claims() finds numeric assertions      │
│   compare() checks against existing entries      │
│   Contradiction → QUARANTINE (log mode default)  │
│                                                   │
│ Stage 4: L0 ECHO                                 │
│   Jaccard word overlap with MEMORY.md entries    │
│   No new content + no external relations         │
│   → QUARANTINE                                   │
│                                                   │
│ All pass → ACCEPT                                │
│                                                   │
│ Verdicts:                                        │
│   ACCEPT → index normally                        │
│   REJECT → not saved, logged                     │
│   QUARANTINE → saved with status=quarantined,    │
│                embedding stripped                 │
│                                                   │
│ Every verdict logged to memory/audit.jsonl       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ STORE — dual backend, fallback chain             │
│                                                   │
│ 1. Try Neo4j (L2b)                              │
│    upsert + compute_associations_single          │
│    If fails → fall through                       │
│                                                   │
│ 2. JSONL fallback (L1b)                          │
│    upsert + compute_backlinks + associations     │
│    Atomic writes (temp file + os.replace)        │
│    fcntl advisory locking                        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ MEMORY.MD UPDATE (L0)                            │
│                                                   │
│ 1. Append entry to MEMORY.md index               │
│ 2. enforce_budget(2000 tokens)                   │
│    Evicts lowest-scoring entries when over budget│
│ 3. categorize_index()                            │
│    Groups entries by type under section headers  │
└─────────────────────────────────────────────────┘
```

---

## 4. Retrieval

### 4.1 Scoring Formula

```
score = recency(0.995^hours) × w_r
      + importance/10         × w_i
      + relevance             × w_v
```

| Mode | Recency (w_r) | Importance (w_i) | Relevance (w_v) |
|------|--------------|-----------------|-----------------|
| Semantic | 0.2 | 0.3 | 0.5 |
| Structured | 0.3 | 0.5 | 0.2 |

When no embedding is available: relevance weight redistributed (40% to recency, 60% to importance).

**Post-sum modifiers:**
- Hub bonus: `+0.05 × ln(1 + backlinks)` — log-scale, diminishing returns
- BM25 text match: up to `+0.3` (JSONL) or `+0.1` substring (Neo4j). Accepted limitation: backends apply different lexical matching.
- MITIGATES dampening: `×0.95` if entry has inbound MITIGATES relations

Score is clamped to `[0.0, 1.0]`.

### 4.2 Variance-Weighted Combiner

The `relevance` component is computed from multi-space embeddings:

```
For each entry:
  per_space_sim[space] = cosine(query_vec, entry_space_vec)
  divergence[space]    = precomputed at embed time

              Σ( sim[space] × divergence[space] )
  relevance = ───────────────────────────────────
                    Σ( divergence[space] )

  default space: weight = 1.0 (always)
  field spaces:  weight = divergence from default
```

**Properties:**
- Distinctive fields (high divergence) are amplified when the query matches them
- Redundant fields (low divergence) are suppressed — they echo default anyway
- No base weights, no query classification, no heuristics
- Entries without divergence profiles fall back to equal weighting
- Single-space entries return their one similarity directly

### 4.3 Type Modifiers

The base recency `0.995^hours` is modified before scoring:

| Type value | Effective recency | Behavior |
|-----------|-------------------|----------|
| `semantic` | `max(recency, 0.6)` | Persists — never decays below 0.6 |
| `procedural` | `recency^(1/(1 + 0.3 × min(access_count, 10)))` | Access-reinforced — more recalls = slower decay |
| Others | `0.995^hours` | Standard exponential decay |

Unrecognised type values receive standard decay. The system does not reject unknown types.

### 4.4 Recall Cascade

```
Query
  → embed query text (Voyage AI)
  → score all active entries
  → select seeds (top-scored)
  → expand at each depth (default 2):
      ├── relations → targets (forward)
      ├── backlinks → sources (reverse)
      └── associations → k-NN neighbors (implicit)
  → re-score expanded set
  → return ranked results (up to limit)
```

Superseded entries are traversable in BFS (their relations are followed) but excluded from results by default. `--include-inactive` overrides this.

---

## 5. Embedding Spaces

### 5.1 Field-to-Space Mapping

Each entity field maps 1:1 to its own embedding space. The default space blends all fields.

| Space | Input | Coverage |
|-------|-------|----------|
| `default` | name + description + observations + prompt + reasoning + chain | 100% |
| `name` | name text only | 100% |
| `description` | description text only | 100% |
| `observations` | observation text joined | 100% |
| `prompt` | prompt text only | ~62% |
| `reasoning` | reasoning text only | ~83% |
| `chain` | chain context text only | varies |

Each space is truncated to 2000 characters. Body text is excluded. Entries missing a field produce no vector for that space (structural absence — combiner skips it).

**Model:** Voyage AI voyage-4-lite, 1024 dimensions per space, up to 7168 dimensions per entry.

### 5.2 Divergence Profile

At embed time, each field space's cosine distance from default is computed:

```
divergence[space] = 1.0 - cosine_similarity(field_vec, default_vec)
```

This is the entry's **structural fingerprint**:
- Low divergence (e.g., observations at 0.08) → field echoes default, redundant
- High divergence (e.g., prompt at 0.40) → field carries unique signal, distinctive

The divergence profile serves two purposes:
1. **Combiner weight** — distinctive fields amplified in scoring
2. **Structural similarity** — entries with similar profiles encode information the same way

---

## 6. Relations

### 6.1 Relation Types

7 typed links connect entities. Relations are authored by the LLM; backlinks are computed as reverse links.

| Type | Direction | Meaning | Side Effects |
|------|-----------|---------|-------------|
| `USES` | A → B | A employs B | — |
| `MODIFIES` | A → B | A changes B | — |
| `DEPENDS_ON` | A → B | A requires B | — |
| `INFORMS` | A → B | A gives context to B | — |
| `SUPERSEDES` | A → B | A replaces B | B.status → superseded, R7 cycle detection |
| `CONTRADICTS` | A ↔ B | A and B conflict | Symmetric edge auto-created on target |
| `MITIGATES` | A → B | A reduces B's impact | B stays active, score × 0.95 |

**Validation rules:** R1 (target+type required), R2 (type must be one of 7 active), R3 (target is valid name), R4 (no self-references), R5 (no duplicate target+type), R6 (referential integrity), R7 (no SUPERSEDES cycles).

### 6.2 Three Connection Types

```
relations    ─────▶   authored at write time (explicit, forward)
backlinks    ◀─────   computed from relations (explicit, reverse)
associations ◀────▶   computed from embeddings (implicit, k-NN)
```

Hub bonus in scoring: `+0.05 × ln(1 + backlinks)`.

---

## 7. Chain Entities

### 7.1 What They Are

A chain entity is a memory that represents an ongoing or completed reasoning sequence. It follows the same schema as any entity — no special structure required.

**Convention (not enforced):**
- Name: `chain-` prefix
- Type: typically `semantic` or `knowledge`
- Observations: ordered steps ("Step 1: ...", "Conclusion: ...")
- Relations: `USES` links to evidence memories
- Chain field: describes the investigation context

### 7.2 Lifecycle

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  START   │────▶│  UPDATE  │────▶│  UPDATE  │────▶│ RELEASE  │
│          │     │          │     │          │     │          │
│ chain    │     │ upsert:  │     │ upsert:  │     │ chain    │
│ start    │     │ obs +=   │     │ obs +=   │     │ release  │
│ <name>   │     │ desc =   │     │ desc =   │     │          │
│          │     │ re-embed │     │ re-embed │     │ READ-    │
│AUTHORISED│     │AUTHORISED│     │AUTHORISED│     │ ONLY     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

- `memoryschema chain start <name>` — authorises the entity for writes
- `memoryschema chain release` — transitions to read-only permanently
- Only one chain can be authorised at a time
- After release, all memories are read-only until a new chain starts

### 7.3 Chain Field

The `chain` field on any memory describes what investigation it belongs to. It is free text with its own embedding space — not a foreign key. Memories with the same chain text cluster naturally through chain-space vector similarity.

### 7.4 Bidirectional Traversal

```
Evidence entry
  ← USES ← Chain entity (via backlink)     → full reasoning in observations
  Chain entity
    → USES → All evidence entries (via relations)
```

Any evidence entry reaches its chain (and all sibling evidence) in two hops.

---

## 8. Authorisation Model

### 8.1 Two States

| State | Write Access | Scope |
|-------|-------------|-------|
| **Unauthorised** (default) | Read-only | All memories after initial write |
| **Authorised** | Read-write (upsert) | Only the active chain entity |

New memories (names not in the store) are always allowed. Upserts to existing names are blocked unless the name matches `memory/.active_chain`.

### 8.2 State Transitions

```
New memory → write → Unauthorised (permanent)
Chain start → Authorised → Chain release → Unauthorised (permanent)
```

At most one authorised entity exists at any time.

---

## 9. Storage Layers

| Layer | Store | Purpose | On Failure |
|-------|-------|---------|-----------|
| L0 | MEMORY.md | Always in prompt context. Token-budget enforced (2000 tokens). Categorized by type. | Never fails |
| L1a | memory/*.md | Git-tracked markdown files. Human-readable XML. | Never fails |
| L1b | store.jsonl | Structured JSONL. Pure Python, stdlib only. Atomic writes. | Never fails |
| L2a | Voyage embeddings | 7 spaces × 1024 dims per entry. Divergence profiles. | Degrades to L1 |
| L2b | Neo4j graph | Relations as edges. Vector k-NN. | Degrades to L2a |

**Degradation chain:**
```
L2b down → L2a still works (embeddings without graph)
L2a down → L1 works (text search only)
L1  down → L0 works (always in prompt, read-only)
```

### 9.1 L0 Budget Enforcement

MEMORY.md is limited to ~2000 tokens (chars/4 approximation). When over budget:
1. Score all indexed entries
2. Evict lowest-scoring entries first
3. Rewrite index
4. Clean up multiple blank lines

Evicted entries remain in L1+ stores — only their L0 visibility is removed.

### 9.2 Progressive Disclosure

After budget enforcement, `categorize_index()` groups MEMORY.md entries under type-based section headers (Knowledge, Procedures, Session History, etc.) for faster scanning.

---

## 10. Validation Rules

### Structure (V1-V12)

| Rule | Check |
|------|-------|
| V1 | File contains exactly one `<memory:entity>` root element |
| V2 | Root element has `name` attribute |
| V3 | `name` attribute matches filename (without .md) |
| V4 | If present, `type` is a non-empty string |
| V5 | If present, `importance` is an integer from 1 to 10 |
| V6 | Contains exactly one `<memory:description>` child element |
| V7 | If present, `<memory:observations>` contains at least one `<memory:observation>` |
| V8 | *(Retired)* |
| V9 | All open tags have matching close tags |
| V10 | If present, `schema` is a valid integer from 1 to current version |
| V11 | If present, `status` is one of: active, superseded, archived, quarantined |
| V12 | If present, `confidence` is an integer from 1 to 10 |

### Relations (R1-R7)

| Rule | Check |
|------|-------|
| R1 | Every relation has both `target` and `type` attributes |
| R2 | `type` is one of the 7 active relation types |
| R3 | `target` is a valid memory name (kebab-case) |
| R4 | No self-references (target ≠ own name) |
| R5 | No duplicate relations (same target+type pair) |
| R6 | Referential integrity — target entity should exist |
| R7 | No SUPERSEDES cycles (A→B→C→A rejected) |

### Filesystem (F1, F3)

| Rule | Check |
|------|-------|
| F1 | Filename matches the `name` attribute |
| F3 | Filename is filesystem-safe (no spaces, special characters beyond hyphens) |

---

## 11. Recall Integration

### 11.1 Automatic Recall

Before answering any user question, the LLM recalls relevant memories:

```bash
memoryschema recall "<user's question or topic>" --limit 3
```

Recalled memories are used as context for the response. The `access()` method tracks recall: increments `access_count` and updates `last_accessed`, which affects future scoring (procedural types decay slower with more accesses).

### 11.2 Recall Pipeline

```
User question
  → LLM runs: memoryschema recall "..." --limit 3
  → System: embed query → score all entries → cascade → return ranked
  → LLM reads results, uses as context
  → LLM responds to user
  → LLM writes memory (chain update or standalone)
```

---

## 12. Audit Trail

All mutations are logged to `memory/audit.jsonl` (append-only):

- **create** — new entity indexed
- **upsert** — existing entity modified (field-level diffs)
- **delete** — entity permanently removed
- **archive** / **unarchive** — status transitions
- **supersede** — SUPERSEDES side effect
- **gate_decision** — write gate verdict with reasons
- **force** — typed force events (contradiction, supersession, world-change, decay)

Tracked fields: description, type, status, importance, confidence, body, prompt, reasoning, chain, project.

---

## 13. CLI Commands

| Command | Purpose |
|---------|---------|
| `memoryschema status` | Store backend, node count, paths |
| `memoryschema recall <query>` | Semantic search with cascade |
| `memoryschema get <name>` | Retrieve single entity |
| `memoryschema list` | List entities (filter by type, project) |
| `memoryschema write <file>` | Parse, validate, gate, embed, index |
| `memoryschema delete <name>` | Permanently remove |
| `memoryschema search <query>` | Full-text keyword search |
| `memoryschema embed --all` | Re-embed entries (--space for field spaces) |
| `memoryschema eval` | Retrieval quality evaluation |
| `memoryschema reflect` | Cluster episodic → synthesize semantic |
| `memoryschema validate` | Schema validation |
| `memoryschema doctor` | 21-point health check |
| `memoryschema chain status/start/release` | Chain lifecycle management |
| `memoryschema neo4j status/deploy/up/down` | Neo4j management |
| `memoryschema hook install/uninstall/status` | Hook management |

---

## 14. Design Principles

1. **Content-agnostic** — the system does not inspect content for trust signals. No provenance labels, no basis attributes, no content classification.
2. **1:1 field-to-space mapping** — each entity field maps to exactly one embedding space. No field appears in two field-specific spaces.
3. **Variance-weighted, not heuristic-weighted** — divergence from default IS the weight. The data determines scoring, not predefined profiles.
4. **Immutable by default** — all memories are read-only after write. Only the active chain can be mutated.
5. **Graceful degradation** — each storage layer works independently. The system functions with just markdown files and MEMORY.md.
6. **Confidence for calibration, not scoring** — confidence is captured at write time for analysis of declared-vs-actual accuracy, without contaminating the retrieval outcomes being measured.
7. **Recall before respond** — the LLM recalls relevant memories before answering, closing the write-read loop.
