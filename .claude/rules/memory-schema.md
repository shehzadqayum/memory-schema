# Memory Schema Rules (v2)

These rules define what a valid memory entity looks like.
They say nothing about when to write or what to capture — that is determined by the scope guidelines.

**Source of truth:** `docs/schema.md` in the memory-schema package. This file is derived from it.

---

## Rule 1: Entity Structure

Every memory entity MUST be a `<memory:entity>` XML block in a `.md` file.

### Required fields (every entity MUST have these):

| Field | Location | Constraints |
|-------|----------|-------------|
| `schema` | attribute | Positive integer. Current: `2`. |
| `name` | attribute | Kebab-case, unique, filesystem-safe. |
| `description` | child element | One-line summary, under 120 characters. |

### Minimal valid entity:

```xml
<memory:entity schema="2" name="unique-identifier">
  <memory:description>One-line summary</memory:description>
</memory:entity>
```

### Full entity (all optional fields):

```xml
<memory:entity schema="2" name="unique-identifier" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact 1</memory:observation>
  </memory:observations>
  <memory:prompt>The user's input that triggered this memory</memory:prompt>
  <memory:reasoning>Narrative thinking — why, alternatives, connections</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
  <memory:source>session-hash-or-provenance</memory:source>
  <memory:project>project-name</memory:project>
</memory:entity>

Optional body text follows after the closing tag.
```

---

## Rule 2: Optional Fields

Include when contextually appropriate. Omit if not relevant.

| Field | Tag | When to include |
|-------|-----|-----------------|
| `importance` | attribute | Integer 1-10. Defaults to 5 if omitted. |
| `type` | attribute | `semantic`, `episodic`, or `procedural`. Defaults to `semantic`. |
| `observations` | `<memory:observations>` | Atomic facts. Must contain at least one `<memory:observation>`. |
| `reasoning` | `<memory:reasoning>` | Narrative thinking — why, alternatives, connections. |
| `prompt` | `<memory:prompt>` | The user input that triggered the response. |
| `relations` | `<memory:relations>` | Explicit links to other known memories. |
| `source` | `<memory:source>` | Provenance (session hash, commit, URL). |
| `project` | `<memory:project>` | Project scoping. |

---

## Rule 3: Type System

Three types. Optional — defaults to `semantic` if omitted.

| Type | Use for |
|------|---------|
| `semantic` | Facts, preferences, references, decisions |
| `episodic` | Events, incidents, implementation history |
| `procedural` | Feedback, validated approaches, patterns |

---

## Rule 4: Relations

Eight typed links connect entities explicitly. All optional.

| Type | Meaning |
|------|---------|
| `USES` | A depends on or employs B |
| `MODIFIES` | A changes or updates B |
| `SUPERSEDES` | A replaces B (B is outdated) |
| `DEPENDS_ON` | A requires B to be true/valid |
| `INFORMS` | A provides context for B |
| `CONTRADICTS` | A and B conflict |
| `PARENT_OF` | A is the parent agent of B |
| `CHILD_OF` | A is a child agent of B |

Rules: target must be a valid memory name. No self-references. No duplicate target+type pairs.

**Hierarchy scoping:** Projects use dot-notation (`parent.child.grandchild`). Parent agents see child memories (containment). Child agents see parent memories during recall (inheritance). Unscoped entities are universally visible.

---

## Rule 5: File Format

- **Filename:** `<name>.md` — matches the `name` attribute exactly.
- **Path:** `memory/<name>.md`
- **Encoding:** XML-escape `<`, `>`, `&`, `"`. Unicode supported.
- **Body:** Optional markdown text after the closing `</memory:entity>` tag.

---

## Rule 6: Upsert Semantics

Re-saving with an existing `name` performs a merge, not a replacement.

| Field | Behavior |
|-------|----------|
| `name` | Immutable |
| `description` | Replaced if provided |
| `observations` | Appended (exact duplicates skipped) |
| `reasoning` | Replaced if provided |
| `prompt` | Replaced if provided |
| `relations` | Deduplicated merge (same target+type not duplicated) |

---

## Rule 7: Retrieval Scoring

```
score = recency(0.995^hours) × w_r + importance/10 × w_i + cosine_similarity × w_v
```

| Query type | Recency | Importance | Relevance |
|------------|---------|------------|-----------|
| Structured | 0.3 | 0.5 | 0.2 |
| Semantic | 0.2 | 0.3 | 0.5 |

---

## Rule 8: Storage Layers

| Layer | Store | On failure |
|-------|-------|------------|
| L0 | MEMORY.md | Never fails (always in context) |
| L1a | Markdown files | Never fails (git-tracked) |
| L1b | JSONL | Never fails (stdlib Python) |
| L2a | Voyage embeddings | Degrades to L1 |
| L2b | Neo4j | Degrades to L2a |

---

## Enforcement

These rules are enforced by:
- **Validator:** V1-V10 (structure), R1-R5 (relations), F1, F3 (filesystem)
- **PostToolUse hook:** Parses, embeds, indexes on every Write to `memory/*.md`
- **Compact resilience:** Working memory entries auto-appended to MEMORY.md by the hook

The schema defines structure. How strictly it is applied depends on the scope guidelines (importance-correlated enforcement).
