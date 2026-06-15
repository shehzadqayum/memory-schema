# Memory Schema Rules (v4)

These rules define what a valid memory entity looks like.
They say nothing about when to write or what to capture — that is determined by the scope guidelines.

**Source of truth:** `docs/schema.md` in the memory-schema package. This file is derived from it.

---

## Rule 1: Entity Structure

Every memory entity MUST be a `<memory:entity>` XML block in a `.md` file.

### Required fields (every entity MUST have these):

| Field | Location | Constraints |
|-------|----------|-------------|
| `schema` | attribute | Positive integer. Current: `4`. |
| `name` | attribute | Kebab-case, unique, filesystem-safe. |
| `description` | child element | One-line summary, under 120 characters. |

### Minimal valid entity:

```xml
<memory:entity schema="4" name="unique-identifier">
  <memory:description>One-line summary</memory:description>
</memory:entity>
```

### Full entity (all optional fields):

```xml
<memory:entity schema="4" name="unique-identifier" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact 1</memory:observation>
  </memory:observations>
  <memory:prompt>The user's input that triggered this memory</memory:prompt>
  <memory:reasoning>Narrative thinking — why, alternatives, connections</memory:reasoning>
  <memory:chain>Reasoning chain context — what investigation this belongs to</memory:chain>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
  <memory:source>session-hash-or-attribution</memory:source>
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
| `type` | attribute | Free-form string. No predefined values enforced. |
| `observations` | `<memory:observations>` | Atomic facts. Must contain at least one `<memory:observation>`. |
| `reasoning` | `<memory:reasoning>` | Narrative thinking — why, alternatives, connections. |
| `prompt` | `<memory:prompt>` | The user input that triggered the response. |
| `chain` | `<memory:chain>` | Reasoning chain context — what investigation this belongs to. |
| `relations` | `<memory:relations>` | Explicit links to other known memories. |
| `source` | `<memory:source>` | Attribution (session hash, commit, URL). |
| `project` | `<memory:project>` | Project scoping. |
| `status` | attribute | `active` (default), `superseded`, `archived`, `quarantined`. |

---

## Rule 3: Type System

The `type` attribute is a free-form string. Optional — defaults to `semantic` when omitted (in parser). No predefined set is prescribed by the validator (any non-empty string accepted). The LLM determines the best value. Consistent usage patterns should emerge organically from the corpus.

The scoring engine recognises `semantic`, `episodic`, `procedural` for recency modifiers. Unrecognised types get standard decay.

---

## Rule 4: Relations

Nine typed links connect entities explicitly (seven active, two deprecated). All optional.

| Type | Meaning |
|------|---------|
| `USES` | A depends on or employs B |
| `MODIFIES` | A changes or updates B |
| `SUPERSEDES` | A replaces B (B is outdated) |
| `DEPENDS_ON` | A requires B to be true/valid |
| `INFORMS` | A provides context for B |
| `CONTRADICTS` | A and B conflict |
| `MITIGATES` | A reduces B's impact without satisfying B's criterion (B stays active) |
| `PARENT_OF` | A is the parent agent of B *(deprecated — use project field)* |
| `CHILD_OF` | A is a child agent of B *(deprecated — use project field)* |

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

Memories are **unauthorised (read-only) by default**. Only the active chain entity is **authorised** for upsert. New memories (names not in store) are always allowed. The active chain is tracked in `memory/.active_chain` — managed via `memoryschema chain start/release`.

When authorised, re-saving with an existing `name` performs a merge:

| Field | Behavior |
|-------|----------|
| `name` | Immutable |
| `project` | Immutable |
| `status` | Replaced (server-managed: set by SUPERSEDES, archive, quarantine) |
| `description` | Replaced if provided |
| `observations` | Appended (exact duplicates skipped) |
| `reasoning` | Replaced if provided |
| `prompt` | Replaced if provided |
| `chain` | Replaced if provided |
| `relations` | Deduplicated merge (same target+type not duplicated) |

---

## Rule 7: Retrieval Scoring

```
score = recency(0.995^hours) × w_r + importance/10 × w_i + relevance × w_v
```

Relevance is computed from multi-space embeddings (7 spaces: default + name + description + observations + prompt + reasoning + chain). The combiner is variance-weighted: each space's similarity is multiplied by its divergence from default (precomputed at embed time). Distinctive fields get amplified, redundant fields suppressed. Falls back to equal weighting when no divergence profile is available.

| Query type | Recency | Importance | Relevance |
|------------|---------|------------|-----------|
| Structured | 0.3 | 0.5 | 0.2 |
| Semantic | 0.2 | 0.3 | 0.5 |

Type factor: semantic `max(recency, 0.6)`, episodic standard decay, procedural `recency^(1/(1+0.3*min(accesses,10)))`.

Basis factor (v4): `measured`=1.0, `inferred`=0.97, `reported`=0.93, unlabelled=1.0 (neutral). Applied after trust multiplier. Lowest-reliability labelled observation determines the factor.

Bonuses: hub `+0.05 * ln(1 + backlinks)`, text match `+0.1` substring (Neo4j) or BM25 up to `+0.3` (JSONL).

---

## Rule 8: Storage Layers

| Layer | Store | On failure |
|-------|-------|------------|
| L0 | MEMORY.md | Never fails (always in context) |
| L1a | Markdown files | Never fails (git-tracked) |
| L1b | JSONL | Never fails (stdlib Python) |
| L2a | Voyage embeddings (7 spaces × 1024 dims) | Degrades to L1 |
| L2b | Neo4j | Degrades to L2a |

---

## Rule 9: Chain Entities

A **chain entity** is a live accumulating memory that grows with each response. It represents an ongoing or completed reasoning sequence.

### Lifecycle
1. **Create** — `memoryschema chain start <name>` authorises the entity. First write creates it.
2. **Update** — the authorised chain accepts upserts (observations append, description/reasoning replace). All other memories are read-only.
3. **Release** — `memoryschema chain release` makes it read-only permanently. Append "Conclusion:" before releasing.
4. **New chain** — only one authorised at a time. Release first, then start a new one.

### Structure
- **Name:** `chain-` prefix (e.g., `chain-why-equal-weight-fails`)
- **Type:** `semantic` (persists with recency floor 0.6)
- **Description:** evolving summary (replaced on each upsert)
- **Observations:** ordered steps — "Step 1: ...", "Step N: ...", "Conclusion: ..." (appended on each upsert)
- **Prompt:** the original trigger (set on create, kept on updates)
- **Reasoning:** evolving narrative (replaced on each upsert)
- **Relations:** `USES` links to evidence memories (accumulated via merge)

### Retrieval
- Embedded in all spaces, re-embedded on every update (embedding stays current)
- Recall cascade follows `USES` to surface evidence
- As semantic type, chain persists (recency floor 0.6) even as evidence decays

---

## Enforcement

These rules are enforced by:
- **Validator:** V1-V14 (structure), R1-R7 (relations), F1, F3 (filesystem)
- **Write gate:** 4-stage pipeline (validation, consistency, numeric probe, L0 echo)
- **PostToolUse hook:** Parses, embeds (7 spaces), gate-checks, indexes on every Write to `memory/*.md`
- **Compact resilience:** Working memory entries auto-appended to MEMORY.md by the hook

The schema defines structure. How strictly it is applied depends on the scope guidelines (importance-correlated enforcement).
