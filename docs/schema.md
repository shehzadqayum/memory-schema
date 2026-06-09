# Memory Schema — `<memory:>` Tag Specification

The memory system has two parts: the **schema** (this document) and the **guidelines** (per-project CLAUDE.md). Together they form the core.

The schema defines an **atomic entity** — a single unit that can be embedded and retrieved. It is intentionally thin: 3 required fields, everything else optional. The schema says what the entity CAN hold. It says nothing about how to use it.

The guidelines determine how the entity IS used — which optional fields to fill, when to write, what scope applies (corpus, working memory, or anything else). Guidelines differ per project.

**Principle:** Schema + guidelines = core. Schema is structure. Guidelines are usage.

**Source of truth:** This document. CLAUDE.md carries a synced copy for prompt injection. Code in `scripts/memory-server/` implements the schema. On divergence, this document wins.

**Schema version:** `2`

**Parser:** `xml.etree.ElementTree` (Python stdlib, zero external dependencies).

---

## Entity Structure

Minimal (required fields only):

```xml
<memory:entity schema="2" name="unique-identifier">
  <memory:description>One-line summary</memory:description>
</memory:entity>
```

Full (all optional fields included):

```xml
<memory:entity schema="2" name="unique-identifier" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact 1</memory:observation>
    <memory:observation>Atomic fact 2</memory:observation>
  </memory:observations>
  <memory:prompt>The user's input that triggered this memory</memory:prompt>
  <memory:reasoning>Narrative thinking — why this approach, what alternatives, what connections</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
  <memory:source>session-hash-or-provenance</memory:source>
  <memory:project>project-name</memory:project>
</memory:entity>

Optional body text follows after the closing tag.
```

---

## Required vs Optional Fields

### Required (every memory must have these)

| Field | Location | Constraints |
| --- | --- | --- |
| **schema** | attribute | Positive integer. Current version: `2`. |
| **name** | attribute | Kebab-case, unique within project, filesystem-safe. |
| **description** | child element | One-line summary, under 120 characters. |

### Optional (include when contextually appropriate)

| Field | Tag | When to include |
| --- | --- | --- |
| **importance** | attribute | Integer 1-10. Defaults to 5 if omitted. |
| **type** | attribute | `semantic`, `episodic`, or `procedural`. Defaults to `semantic` if omitted. |
| **observations** | `<memory:observations>` | Atomic facts. Include when there are discrete facts to record. |
| **reasoning** | `<memory:reasoning>` | Narrative thinking — why, alternatives, connections. |
| **prompt** | `<memory:prompt>` | The user input that triggered the response. |
| **relations** | `<memory:relations>` | When the memory explicitly relates to other known memories. |
| **source** | `<memory:source>` | To record provenance (session hash, commit, URL). |
| **project** | `<memory:project>` | When the memory is project-scoped (omit for user-scope). |

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

### Rules

- **Format:** Positive integer (1, 2, 3...), not semver
- **Missing attribute:** Treated as schema version 1 (backward compatibility)
- **Validation:** V10 checks the attribute is a valid integer not exceeding the current version
- Existing v1 files remain valid — v2 adds optional fields only

---

## Type System

Three memory types. Optional — defaults to `semantic` if omitted.

**Note:** The retention descriptions below are design intent, not current implementation. The scoring formula applies uniform recency decay (0.995^hours) to all types. Type-differentiated retention (persistent semantic, decaying episodic, access-reinforced procedural) would require a type term in the scoring formula, which has not been implemented.

### `semantic` — Facts and Concepts

**Intended retention:** Persists indefinitely. Updated on correction.
**Use for:** preferences, references, domain knowledge, architectural decisions.

### `episodic` — Experiences and Events

**Intended retention:** Ages faster via recency decay.
**Use for:** decisions, incidents, debugging sessions, implementation history.

### `procedural` — Skills and Approaches

**Intended retention:** Reinforced by access (each recall strengthens).
**Use for:** feedback, validated approaches, corrected behaviors, workflow patterns.

---

## Relation Types

Six relation types define explicit connections between memories.

| Type | Direction | Meaning |
| --- | --- | --- |
| `USES` | A → B | A depends on or employs B |
| `MODIFIES` | A → B | A changes or updates B |
| `SUPERSEDES` | A → B | A replaces B (B is outdated) |
| `DEPENDS_ON` | A → B | A requires B to be true/valid |
| `INFORMS` | A → B | A provides context for B |
| `CONTRADICTS` | A ↔ B | A and B conflict |

**Rules:** Target must be a valid memory name. No self-references. No invented types. Deduplicated on upsert.

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

**Path:** `memory/<name>.md` (project-scoped) or `memory/user/<name>.md` (user-scoped).

**Structure:** `<memory:entity>` block followed by optional body text (markdown) after the closing tag.

**Attributes promoted to root:** `schema`, `name` (required); `importance`, `type` (optional, default to 5 and `semantic` respectively). All other fields are child elements.

**Encoding:** XML-escape `<`, `>`, `&`, `"`. Unicode supported. Omit empty optional fields entirely.

---

## Upsert Semantics

Re-saving with an existing `name` performs a merge, not a replacement.

| Field | Behavior |
| --- | --- |
| **name** | Immutable |
| **type** | Updated if provided |
| **description** | Updated if provided |
| **importance** | Updated if provided |
| **observations** | Appended (exact duplicates skipped) |
| **reasoning** | Replaced if provided |
| **prompt** | Replaced if provided |
| **relations** | Deduplicated merge (same target+type not duplicated) |
| **body** | Replaced if provided |
| **source** | Updated if provided |
| **project** | Immutable |

---

## Validation Rules

### Structure

| Rule | Description |
| --- | --- |
| V1 | File contains exactly one `<memory:entity>` root element |
| V2 | Root element has `name` attribute |
| V3 | `name` attribute matches the filename (without `.md` extension) |
| V4 | If present, `type` is one of: `semantic`, `episodic`, `procedural` |
| V5 | If present, `importance` is an integer from 1 to 10 |
| V6 | Contains exactly one `<memory:description>` child element |
| V7 | If present, `<memory:observations>` contains at least one `<memory:observation>` |
| V8 | *(Retired — formerly required `<memory:observations>`, now optional)* |
| V9 | All open tags have matching close tags |
| V10 | If present, `schema` attribute is a valid integer from 1 to current version |

### Relations

| Rule | Description |
| --- | --- |
| R1 | Every `<memory:relation>` has both `target` and `type` attributes |
| R2 | `type` is one of the six defined types |
| R3 | `target` is a valid memory name (kebab-case) |
| R4 | No self-references (target != own name) |
| R5 | No duplicate relations (same target + type pair) |

### File System

| Rule | Description |
| --- | --- |
| F1 | Filename matches the `name` attribute: `<name>.md` |
| F2 | File is in the correct directory for its scope |
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

When embedding unavailable: relevance weight redistributed (structured: 0.4 recency, 0.6 importance).

**Properties:** No explicit tiers. Frequently accessed memories score higher. Connected memories rank higher. Neglected memories decay (0.89 at 24h, 0.70 at 72h, 0.43 at 7d). Important memories resist decay.

---

## Storage Layers

Each layer adds capability without being required. The system degrades gracefully.

| Layer | Store | Purpose | On failure |
| --- | --- | --- | --- |
| L0 | MEMORY.md | Always-in-context index | Never fails |
| L1a | Markdown files | Persistence, git, human-readable | Never fails |
| L1b | JSONL | Structured queries, backlinks, access tracking | Never fails |
| L2a | Voyage embeddings | Semantic similarity, associations | Degrades to L1 |
| L2b | Neo4j (`ict-neo4j`) | Primary store, vector k-NN, graph traversal | Degrades to L2a |

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

---

## Behavioral Specification

**On Create:** Write markdown → upsert Neo4j (or JSONL fallback) → embed → associations → append to MEMORY.md (working memory only).
**On Access:** Increment access_count, update last_accessed.
**On Query:** Score candidates → search → expand via backlinks+associations → return ranked.
**On Consolidate:** Sync un-indexed files → backlinks → (batch embed → associations → Neo4j if available).

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
