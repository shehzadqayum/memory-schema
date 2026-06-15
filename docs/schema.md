# Memory Schema — `<memory:>` Tag Specification

The memory system has two parts: the **schema** (this document) and the **guidelines** (per-project CLAUDE.md). Together they form the core.

The schema defines an **atomic entity** — a single unit that can be embedded and retrieved. It is intentionally thin: 3 required fields, everything else optional. The schema says what the entity CAN hold. It says nothing about how to use it.

The guidelines determine how the entity IS used — which optional fields to fill, when to write, what scope applies (corpus, working memory, or anything else). Guidelines differ per project.

**Principle:** Schema + guidelines = core. Schema is structure. Guidelines are usage.

**Source of truth:** This document. `.claude/rules/memory-schema.md` carries a derived copy. On divergence, this document wins.

**Schema version:** `4`

**Parser:** `xml.etree.ElementTree` (Python stdlib, zero external dependencies).

---

## Entity Structure

Minimal (required fields only):

```xml
<memory:entity schema="4" name="unique-identifier">
  <memory:description>One-line summary</memory:description>
</memory:entity>
```

Full (all optional fields included):

```xml
<memory:entity schema="4" name="unique-identifier" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact 1</memory:observation>
    <memory:observation>Atomic fact 2</memory:observation>
  </memory:observations>
  <memory:prompt>The user's input that triggered this memory</memory:prompt>
  <memory:reasoning>Narrative thinking — why this approach, what alternatives, what connections</memory:reasoning>
  <memory:chain>Reasoning chain context — what investigation this belongs to</memory:chain>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
  <memory:project>project-name</memory:project>
</memory:entity>

Optional body text follows after the closing tag.
```

---

## Required vs Optional Fields

### Required (every memory must have these)

| Field | Location | Constraints |
| --- | --- | --- |
| **schema** | attribute | Positive integer. Current version: `4`. |
| **name** | attribute | Kebab-case, unique within project, filesystem-safe. |
| **description** | child element | One-line summary, under 120 characters. |

### Optional (include when contextually appropriate)

| Field | Tag | When to include |
| --- | --- | --- |
| **importance** | attribute | Integer 1-10. Defaults to 5 if omitted. |
| **confidence** | attribute | Integer 1-10. Author's confidence in this memory. Optional; when omitted, no effect. Write-time metadata — does not affect retrieval scoring. V12 enforces range. |
| **type** | attribute | Free-form string. No predefined values enforced. LLM determines best usage. |
| **observations** | `<memory:observations>` | Atomic facts. Include when there are discrete facts to record. |
| **reasoning** | `<memory:reasoning>` | Narrative thinking — why, alternatives, connections. |
| **prompt** | `<memory:prompt>` | The user input that triggered the response. |
| **chain** | `<memory:chain>` | Reasoning chain context — what investigation this belongs to. |
| **relations** | `<memory:relations>` | When the memory explicitly relates to other known memories. |
| **project** | `<memory:project>` | When the memory is project-scoped (omit for user-scope). |
| **status** | attribute | `active` (default), `superseded`, `archived`, or `quarantined`. |

### Server-managed (never authored by Claude)

| Field | Tag | Purpose |
| --- | --- | --- |
| **created_at** | `<memory:created_at>` | ISO 8601 timestamp of first save |
| **last_accessed** | `<memory:last_accessed>` | ISO 8601 timestamp of last recall |
| **access_count** | `<memory:access_count>` | Number of times recalled |
| **backlinks** | `<memory:backlinks>` | Reverse links from other memories' relations |
| **associations** | `<memory:associations>` | k-nearest neighbors from embedding space |
| **embedding** | `<memory:embedding>` | Voyage vector metadata (stored in JSONL) |
| **embedded_at** | `<memory:embedded_at>` | When embedding was computed |

---

## Schema Versioning

| Version | Changes |
| --- | --- |
| `1` | Initial tagged schema. |
| `2` | Added `<memory:prompt>` and `<memory:reasoning>` as optional fields. Removed save/recall/result/consolidation MCP tags (unimplemented interfaces). Removed observation grammar (moved to project guidelines). Moved `<memory:observations>`, `type`, and `importance` from required to optional. Required fields reduced to: schema, name, description. All other fields optional. |
| `3` | Added `status` attribute. Deprecated `PARENT_OF`, `CHILD_OF` relations (use `project` field). Added V11 (status), R6 (referential integrity), R7 (SUPERSEDES cycle detection). Full backward compatible with v1/v2. |
| `4` | Added `MITIGATES` relation type (7 active, 9 total). Added `confidence` attribute (1-10). Added `chain` field. 7 embedding spaces with variance-weighted combiner. Authorised/unauthorised memory states. Content-agnostic (no trust labels). Backward compatible with v1–v3. |

### Rules

- **Format:** Positive integer (1, 2, 3...), not semver
- **Missing attribute:** Treated as schema version 1 (backward compatibility)
- **Validation:** V10 checks the attribute is a valid integer not exceeding the current version
- Existing v1 files remain valid — v2 adds optional fields only

---

## Type System

The `type` attribute is a free-form string. Optional — defaults to `semantic` when omitted (in parser). The LLM determines the best value based on the content being captured. No predefined set is prescribed by the validator (any non-empty string accepted). Consistent usage patterns should emerge organically from the corpus over time.

**Type factor in scoring:** The scoring engine recognises three type values for recency modification (`semantic`, `episodic`, `procedural`). Unrecognised types receive standard decay. If the LLM converges on these names organically, the scoring benefits activate. See Retrieval Scoring for the formulas.

---

## Relation Types

Nine relation types define explicit connections between memories (seven active, two deprecated).

| Type | Direction | Meaning |
| --- | --- | --- |
| `USES` | A → B | A depends on or employs B |
| `MODIFIES` | A → B | A changes or updates B |
| `SUPERSEDES` | A → B | A replaces B (B is outdated) |
| `DEPENDS_ON` | A → B | A requires B to be true/valid |
| `INFORMS` | A → B | A provides context for B |
| `CONTRADICTS` | A ↔ B | A and B conflict |
| `MITIGATES` | A → B | A reduces the impact of B without satisfying B's criterion. B remains active. |
| `PARENT_OF` | A → B | A is the parent agent of B *(deprecated — use project field)* |
| `CHILD_OF` | A → B | A is a child agent of B *(deprecated — use project field)* |

**Rules:** Target must be a valid memory name. No self-references. No invented types. Deduplicated on upsert.

### Dot-Notation Project Hierarchy

Projects use dot-notation to encode agent nesting: `parent.child.grandchild`.

```
parse_project_path('org.team.sub')  →  ['org', 'team', 'sub']
parent_project('org.team.sub')      →  'org.team'
ancestor_projects('org.team.sub')   →  ['org.team', 'org']
```

Each segment must be kebab-case. No leading/trailing dots. No empty segments.

### Hierarchy Scoping

Two matching modes control memory visibility across the hierarchy:

**Bidirectional (recall)** — `project_matches_scope(entry, scope)`:
- Child sees parent memories (inheritance)
- Parent sees child memories (containment)
- Unscoped entities (no project field) are universally visible
- Optional `max_depth` limits how many levels up/down a match can reach

**Subtree-only (search/list)** — `project_matches_filter(entry, filter)`:
- Parent sees children (containment)
- Children do NOT see parent (no upward inheritance)
- Unscoped entities are universally visible

### Three Connection Types

```
relations     ------>  authored at save time (forward, explicit)
backlinks     <------  computed from relations (reverse, discovered)
associations  <----->  computed from embeddings (implicit, emergent)
```

Memories connected to other memories rank higher in retrieval.

---

## File Format

**Filename:** `<name>.md` — matches the `name` attribute exactly.

**Path:** `memory/<name>.md`. Project scoping is via the `<memory:project>` element, not directory structure.

**Structure:** `<memory:entity>` block followed by optional body text (markdown) after the closing tag.

**Attributes promoted to root:** `schema`, `name` (required); `importance`, `type` (optional, default to 5 and `semantic` respectively). All other fields are child elements.

**Encoding:** XML-escape `<`, `>`, `&`, `"`. Unicode supported. Omit empty optional fields entirely.

---

## Upsert Semantics

Re-saving with an existing `name` performs a merge, not a replacement, **subject to authorisation**.

### Authorisation Gate

Memories have two write states:

| State | Write access | When |
|-------|-------------|------|
| **Unauthorised** (default) | Read-only | All memories after initial write |
| **Authorised** | Read-write (upsert allowed) | Only the active chain entity |

Only ONE memory can be authorised at a time: the active chain, tracked in `memory/.active_chain` (a system-managed singleton file). The hook checks this file before allowing upserts. New memories (names that don't exist in the store) are always allowed. Upserts to existing unauthorised memories are silently skipped.

- `memoryschema chain start <name>` → authorises the named entity for writes
- `memoryschema chain release` → transitions it to unauthorised (read-only, permanent)

### Merge behavior (when authorised)

| Field | On Create | On Merge |
|-------|-----------|----------|
| `name` | Set (merge key) | Immutable |
| `schema` | Set | Immutable |
| `project` | Set | Immutable |
| `filepath` | Set | Immutable |
| `created_at` | Set (auto) | Immutable |
| `type` | Set | Replaced if provided |
| `description` | Set | Replaced if provided |
| `importance` | Set | Replaced if provided |
| `status` | Set | Replaced (server-managed: auto-set by SUPERSEDES, archive, quarantine) |
| `observations` | Set | Appended (exact duplicates skipped) |
| `reasoning` | Set | Replaced if provided |
| `prompt` | Set | Replaced if provided |
| `chain` | Set | Replaced if provided |
| `relations` | Set | Appended (deduped by target+type) |
| `body` | Set | Replaced if provided |

---

## Validation Rules

### Structure

| Rule | Description |
| --- | --- |
| V1 | File contains exactly one `<memory:entity>` root element |
| V2 | Root element has `name` attribute |
| V3 | `name` attribute matches the filename (without `.md` extension) |
| V4 | If present, `type` is a non-empty string (free-form, no predefined values) |
| V5 | If present, `importance` is an integer from 1 to 10 |
| V6 | Contains exactly one `<memory:description>` child element |
| V7 | If present, `<memory:observations>` contains at least one `<memory:observation>` |
| V8 | *(Retired — formerly required `<memory:observations>`, now optional)* |
| V9 | All open tags have matching close tags |
| V10 | If present, `schema` attribute is a valid integer from 1 to current version |
| V11 | If present, `status` is one of: active, superseded, archived, quarantined |
| V12 | If present, `confidence` is an integer from 1 to 10 |

### Relations

| Rule | Description |
| --- | --- |
| R1 | Every `<memory:relation>` has both `target` and `type` attributes |
| R2 | `type` is one of the seven active relation types (deprecated types warned) |
| R3 | `target` is a valid memory name (kebab-case) |
| R4 | No self-references (target != own name) |
| R5 | No duplicate relations (same target + type pair) |
| R6 | Referential integrity — target entity should exist (warning in standard, error in strict) |
| R7 | No SUPERSEDES cycles — adding A→B→...→A chains is rejected |

### File System

| Rule | Description |
| --- | --- |
| F1 | Filename matches the `name` attribute: `<name>.md` |
| F3 | Filename is filesystem-safe (no spaces, special characters beyond hyphens) |

---

## Retrieval Scoring

```
retrieval_score =
    recency(0.995 ^ hours_since_access)  x  weight_recency
  + (importance / 10)                     x  weight_importance
  + cosine_similarity(query, memory)      x  weight_relevance
```

| Query type | Recency | Importance | Relevance |
| --- | --- | --- | --- |
| Exact lookup | No scoring (direct return) | | |
| Structured | 0.3 | 0.5 | 0.2 |
| Semantic | 0.2 | 0.3 | 0.5 |

When embedding unavailable: relevance weight redistributed (40% to recency, 60% to importance).

**Bonuses** (added after weighted sum, before clamping to 1.0):

| Bonus | Value | Condition |
| --- | --- | --- |
| Hub bonus | `+0.05 * ln(1 + backlinks)` | Entry has backlinks (log-scale, diminishing returns) |
| Text match | `+0.1` substring (Neo4j) or BM25 up to `+0.3` (JSONL) | Query text relevance boost. **Accepted limitation:** the two backends apply different lexical matching; identical queries may rank differently across the degradation chain. |

### Type Factor

The base recency `0.995^hours` is modified by the entry's type before being used in the score formula:

| Type | Effective recency | Behavior |
|------|-------------------|----------|
| `semantic` | `max(recency, 0.6)` | Floor at 0.6 — facts never fully decay |
| `episodic` | `recency` | Standard decay — events age naturally |
| `procedural` | `recency^(1/(1 + 0.3*min(access_count, 10)))` | Access-reinforced — frequently used procedures resist decay |

Procedural examples: 0 accesses → standard decay; 5 accesses → exponent 0.4 (slower); 10 accesses → exponent 0.25 (very slow).

**Properties:** No explicit tiers. Frequently accessed memories score higher. Connected memories rank higher via hub bonus. Neglected memories decay (0.89 at 24h, 0.70 at 72h, 0.43 at 7d). Important memories resist decay.

---

## Embedding Spaces

Each entity is embedded in up to 7 independent vector spaces (1024 dims each, Voyage AI voyage-4-lite). Architecture: 1:1 field-to-space mapping, plus a default blend of all fields.

| Space | Input fields | Coverage | Purpose |
|-------|-------------|----------|---------|
| `default` | name + description + observations + prompt + reasoning + chain | 100% | Full semantic blend |
| `name` | name only | 100% | Identity matching |
| `description` | description only | 100% | Topic identity |
| `observations` | observation text only | 100% | Fact-level matching |
| `prompt` | prompt only | ~62% | Intent matching |
| `reasoning` | reasoning only | ~83% | Rationale matching |
| `chain` | chain context only | varies | Reasoning chain grouping |

Each space is truncated to 2,000 characters. Body text is **excluded** (it may contain unstructured markdown or code that degrades embedding quality). Entries missing a field produce no vector for that space (structural absence — the combiner skips absent spaces, never counts them as zero).

The canonical composition function is `compose_embedding_text(entry, space='default')` in `embedding_input.py`. All callers must use this function.

**Variance-weighted combiner:** Each space's cosine similarity with the query is multiplied by the space's divergence from default (precomputed at embed time as `divergence_profile`). Distinctive fields (high divergence) get amplified when the query matches them. Redundant fields (low divergence) get suppressed. No base weights, no query classification — the data determines the weights.

Reasoning has a soft length ceiling of 500 words (strict-mode quality check Q8).

---

## Storage Layers

Each layer adds capability without being required. The system degrades gracefully.

| Layer | Store | Purpose | On failure |
| --- | --- | --- | --- |
| L0 | MEMORY.md | Always-in-context index | Never fails |
| L1a | Markdown files | Persistence, git, human-readable | Never fails |
| L1b | JSONL | Structured queries, backlinks, access tracking | Never fails |
| L2a | Voyage embeddings | 7 spaces × 1024 dims, semantic similarity, associations | Degrades to L1 |
| L2b | Neo4j | Primary store, vector k-NN, graph traversal | Degrades to L2a |

### Fallback Chain

```
Full stack:    markdown + JSONL + embedding + graph → scored retrieval
Voyage down:   markdown + JSONL → structured queries only
Neo4j down:    markdown + JSONL + embedding → similarity without graph
Everything:    markdown + MEMORY.md → Read tool (always works)
```

---

## MEMORY.md Index

Layer 0 — always in context. One line per entry:

```markdown
- [Name](filename.md) -- one-line description
```

Stays under 200 lines (auto-load limit). The PostToolUse hook automatically appends working memory entries to MEMORY.md on write, ensuring they remain visible after `/compact` events (compact resilience).

**L0 budget enforcement:** When MEMORY.md exceeds the token budget (default: 2000 tokens, configurable via `l0_token_budget`), the lowest-scoring entries are evicted. Token estimation uses chars/4 approximation. If no store is available for scoring, eviction falls back to FIFO (oldest first).

**Progressive disclosure:** After budget enforcement, `categorize_index()` reorganizes MEMORY.md entries into type-based sections (Knowledge, Procedures, Session History) for faster scanning.

---

## Behavioral Specification

**On Create:** Write markdown → authorisation check → write gate → embed (if accepted) → upsert → associations → append to MEMORY.md (working memory only). New names always allowed; existing names require active chain authorisation.

### Write Gate Pipeline

Every write passes through a four-stage gate before indexing. Embedding is computed BEFORE the gate (stages 4-6 need the vector). The gate never silently drops — every entry receives a logged verdict.

```
Parse → Embed (7 spaces) → Gate Pipeline → Index
                                │
                  ┌─────────────┼─────────────┐
                  │             │             │
               ACCEPT      QUARANTINE      REJECT
             (index)     (save unembedded,  (not saved,
                          status=quarantined)  exit with error)
```

| Stage | Check | Failure verdict |
|-------|-------|-----------------|
| 1. Validation | Name required, description expected | REJECT |
| 2. Consistency probe | Near-duplicate (>0.95 cosine sim, different description) | QUARANTINE |
| 3. Numeric probe | Contradiction with existing entries (extract_claims matching) | QUARANTINE (log mode) |
| 4. L0 echo probe | Restatement check (Jaccard overlap + measured conjunction) | QUARANTINE |

Every gate decision is recorded in `memory/audit.jsonl` with machine-readable verdict and reasons.
**On Access:** Increment access_count, update last_accessed.
**On Query:** Score candidates → search → expand via backlinks+associations → return ranked. Non-active entries are excluded from results by default (`--include-inactive` to override). Superseded entries remain traversable in BFS graph walks (their relations are followed) but are not returned in results.
**On Consolidate:** Sync un-indexed files → backlinks → (batch embed → associations → Neo4j if available).
**On Reflect:** Cluster episodic entries → synthesize semantic summaries:
1. Build adjacency graph from mutual k-NN associations (filtered by score_threshold, default 0.7)
2. Find connected components via BFS (min/max cluster size filtering)
3. Synthesize summary: tries LLM via Anthropic SDK, falls back to mechanical merge (concatenate descriptions, dedup observations)
4. Create SUPERSEDES edges from summary to cluster members
5. Set summary importance to max of cluster
6. Archive original episodic entries (status → superseded)

### Lifecycle Events

**On Supersede:** When a SUPERSEDES relation is created:
1. Cycle detection checked (R7)
2. Target entry status set to `superseded`
3. Target removed from MEMORY.md (on explicit CLI write; hook manages L0)
4. Target remains traversable in recall BFS but excluded from results
5. Audit logged

**On Archive:** When `memoryschema archive NAME` is invoked:
1. Entry status set to `archived` in store
2. Entry removed from MEMORY.md
3. Entry excluded from default recall/search/list
4. Audit logged

**On Delete:** When `memoryschema delete NAME --confirm` is invoked:
1. Entry removed from JSONL store (or Neo4j via DETACH DELETE)
2. All inbound relations pointing to entry cleaned up
3. All backlink references removed
4. Markdown file (`memory/<name>.md`) deleted from disk
5. Entry removed from MEMORY.md
6. Audit logged — deletion is permanent and irreversible

**On Quarantine:** When the write gate quarantines an entry:
1. Entry saved with `status=quarantined`
2. Embedding skipped (stored unembedded)
3. Entry excluded from default recall/search/list
4. Gate decision audit-logged with verdict + reasons
5. Entry available for review via `memoryschema quarantine review`

**On Mutate (Upsert):** When an existing entry is re-upserted (must be the authorised active chain):
1. Authorisation check (name must match `memory/.active_chain`)
2. Write gate evaluates the mutation
2. Immutable fields preserved (name, schema, project, filepath, created_at)
3. Observations appended (exact duplicates skipped)
4. Relations appended (same target+type deduplicated)
5. SUPERSEDES/CONTRADICTS side effects processed
6. Prior state captured for audit diff
7. Audit logged with field-level change hashes

### Status Transitions

| Transition | Trigger | Effect | CLI |
|------------|---------|--------|-----|
| active → superseded | SUPERSEDES relation created | Target marked superseded, removed from MEMORY.md | Automatic via `write` |
| active → archived | User request | Excluded from recall/search, removed from MEMORY.md | `memoryschema archive NAME` |
| active → quarantined | Write gate suspicion | Excluded from recall/search, stored unembedded | Write gate (Phase 4) |
| archived → active | User request | Re-included in recall/search | `memoryschema unarchive NAME` |
| superseded → active | User request | Re-included in recall/search | `memoryschema reactivate NAME` |
| quarantined → active | Review approval | Embedded and included in recall/search | `memoryschema quarantine release NAME` |
| quarantined → deleted | Review rejection | Permanently removed from all stores | `memoryschema quarantine reject NAME --confirm` |

### SUPERSEDES Integrity

- **Cycle detection (R7):** Adding a SUPERSEDES relation that would create a circular chain (A→B→C→A) is rejected with a ValueError.

### Upsert Immutability

See the consolidated upsert table in §Upsert Semantics above.

---

## Chain Entities

A **chain entity** is a memory that represents a sequence of reasoning steps from trigger to conclusion. It is a regular entity — no schema changes required — that follows a specific pattern:

### Structure

- **Type:** `semantic` (chains persist as knowledge distillation)
- **Name:** prefix with `chain-` (e.g., `chain-why-equal-weight-fails`)
- **Description:** "Chain: <conclusion summary>"
- **Observations:** Ordered steps — "Step 1: ...", "Step 2: ...", "Conclusion: ..."
- **Prompt:** The trigger question the chain answers
- **Reasoning:** Why the chain matters, connecting the steps
- **Relations:** `USES` links to each evidence memory referenced by the steps

### Example

```xml
<memory:entity schema="4" name="chain-why-x-fails" type="semantic" importance="8">
  <memory:description>Chain: X fails because of Y — proven through 3 experiments</memory:description>
  <memory:observations>
    <memory:observation>Step 1: Tried approach A, measured result P</memory:observation>
    <memory:observation>Step 2: Tried approach B, measured result Q</memory:observation>
    <memory:observation>Step 3: Compared P and Q, found Q better</memory:observation>
    <memory:observation>Conclusion: Y is the root cause, B is the fix</memory:observation>
  </memory:observations>
  <memory:prompt>Why does X fail?</memory:prompt>
  <memory:reasoning>Each experiment isolated a variable...</memory:reasoning>
  <memory:relations>
    <memory:relation target="evidence-memory-1" type="USES"/>
    <memory:relation target="evidence-memory-2" type="USES"/>
  </memory:relations>
</memory:entity>
```

### Retrieval Behavior

- The chain entity is embedded in all spaces — findable by trigger question, conclusion, or any step
- Recall cascade follows `USES` relations to surface the evidence memories (depth 1-2)
- As a semantic type, the chain has a recency floor of 0.6 — it persists even as episodic evidence steps decay
- This creates natural knowledge distillation: the chain is the durable summary, the evidence is the decayable detail

### Lifecycle

Chain entities are **live accumulating** — they grow with each response in a session:

1. **Create** — `memoryschema chain start <name>` authorises the entity for writes. First response creates `memory/<name>.md` with Step 1.
2. **Update** — the authorised chain accepts upserts. Observations append (each step adds). Description and reasoning are replaced (evolving summary). Relations merge (USES links accumulate). All other memories remain unauthorised (read-only).
3. **Release** — `memoryschema chain release` transitions the chain to unauthorised (read-only, permanent). Append a "Conclusion:" observation before releasing.
4. **New chain** — if the topic changes, release the current chain and start a new one. Only one chain can be authorised at a time.

The embedding is re-computed on every upsert (the hook fires on every write), so the chain's vector representation stays current as it grows.

### When to Create

Create a chain entity when:
- Starting a new session or conversation
- A multi-step investigation begins
- An experiment starts sequential steps
- A debugging session begins a hypothesis → test → revise cycle
- A design evaluation starts comparing alternatives

---

## Design Decisions

| Decision | Rationale |
| --- | --- |
| Body after closing tag | Free-form markdown, not structured data |
| Attribute promotion | `name`, `type`, `importance` as root attributes for compact representation |
| `memory:` prefix cosmetic | Not a real XML namespace — stripped before parsing |
| XML escaping required | No CDATA support — keeps parser simple |
| Strict mode optional | Quality checks (kebab-case name, description length, atomic observations) in strict only — defined in `validator.py`, not in this document. Graceful handling of imperfect output |
| v1 backward compatible | v2 adds optional fields only — all v1 files remain valid |
| v3 | Adds `status` attribute. Deprecates `PARENT_OF`, `CHILD_OF` relations. Adds V11, R6, R7 validation rules. |
| v4 (current) | Adds `MITIGATES` relation, `confidence` attribute, `chain` field, 7 embedding spaces, variance-weighted combiner, authorised/unauthorised states. Content-agnostic. |
