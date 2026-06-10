# Memory System — Overview

The memory system has two parts: the **schema** and the **guidelines**. Together they form the core.

- **Schema** (`docs/schema.md`) — defines the entity structure. Intentionally thin: 3 required fields, everything else optional. The schema says what the entity CAN hold. It is the same across all projects.
- **Guidelines** (`.claude/rules/memory-*.md`) — defines how to fill the entity. Which optional fields to use, when to write, what scope applies. Guidelines differ per project and per scope.

Everything else — the store, embeddings, hooks, scripts — is infrastructure that serves the core.

## The Memory Entity

A memory is a single, atomic unit of storage. It has a name, a description, and optionally any combination of observations, reasoning, prompt, relations, and source. Every memory uses the same structure:

```xml
<memory:entity schema="2" name="unique-name" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>A specific fact</memory:observation>
  </memory:observations>
  <memory:prompt>What was asked</memory:prompt>
  <memory:reasoning>Why this answer, what alternatives, what connections</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="INFORMS"/>
  </memory:relations>
  <memory:source>provenance</memory:source>
</memory:entity>
```

The entity is general-purpose. What determines how it is **used** — as a document in a corpus or as a working note from a session — is the guidance, not the schema.

## Two Scopes, One Entity

### Working Memory

Session reasoning — what was asked, what was decided, why. Selective enforcement (write when a decision, correction, or novel fact is established).

- `<memory:prompt>` holds the user's input
- `<memory:reasoning>` holds the narrative thinking
- `<memory:observation>` holds atomic facts

### Corpus Memory

Ingested content — documents, posts, articles. Batch enforcement (ingested via scripts). Importance reflects source salience.

- `<memory:observation>` holds the source text
- No `<memory:prompt>` or `<memory:reasoning>` (content was ingested, not generated)
- Importance computed from source signals (engagement, authorship)

### Why They Don't Compete

Working memory and corpus memory occupy different regions of the embedding space. Queries about trading concepts find corpus entries. Queries about system decisions find working memory. The embeddings naturally separate them.

## How Retrieval Works

1. **Embed the query** — convert to a 1,024-dimensional vector via Voyage AI
2. **Score all entries** — combine relevance (50%), importance (30%), recency (20%)
3. **Find seeds** — top 3 scoring entries
4. **Cascade** — expand through relations, backlinks, and associations
5. **Return ranked results**

## Storage

Each entity exists in up to three forms:
1. **Markdown file** (L1a) — human-readable, git-tracked
2. **JSONL line** (L1b) — machine-readable, with embedding vector
3. **Neo4j node** (L2b) — primary store, with vector index and graph edges

The system degrades gracefully. If Neo4j is down, JSONL works. If JSONL is corrupted, markdown files survive. If everything fails, MEMORY.md is always in context.

**Compact resilience:** The PostToolUse hook appends working memory entries to MEMORY.md on write. After a `/compact` event, all working memory remains visible.

## Schema + Guidelines = Core

- **Schema** (structure): 3 required fields, 8 optional. Portable across projects.
- **Guidelines** (usage): per-scope, per-project. Importance correlates with enforcement.

The schema is stable (changes rarely). The guidelines are tunable (change per project, per session, per scope).

## Diagnostics

`memoryschema doctor` is the health check entry point. It runs 21 checks against the live system — Python, package, config, filesystem, Docker, Neo4j, Voyage AI, hook, tests — and reports status with self-documented remediation for any failures.

```bash
memoryschema doctor          # Human-readable report
memoryschema doctor --json   # Machine-readable for agents
memoryschema doctor --fix    # Auto-remediation suggestions
```

Every failed check prints what went wrong and the exact command to fix it.

## Agent Hierarchy

Each project folder is an agent. Agents nest via dot-notation: `parent.child.grandchild`.

**Containment model:** Parent's scope includes everything in the child's scope. Agents communicate through shared memories — the memory graph is the communication bus.

**Memory visibility:**
- Parent always sees child memories (containment)
- Child sees parent memories during recall (inheritance)
- Unscoped entities (no project field) are universally visible

## Configuration Inheritance

Config via `memoryschema.toml` files. Resolution order (highest to lowest):

```
1. CLI flags                 (--project, --root — explicit user intent)
2. Environment variables     (NEO4J_URI, VOYAGE_API_KEY, etc.)
3. Parent memoryschema.toml  (parent wins over child on conflict)
4. Child memoryschema.toml
5. Dataclass defaults
```

**Parent-absolute authority:** Parent's config values override child's. Child can only set values the parent didn't define. Child has full autonomy when parent is absent.

Use `memoryschema config --chain` to inspect the resolution chain.

## Rules Inheritance

Rules are `.claude/rules/*.md` files. Inheritance follows the same parent-wins model:

- Parent's rule replaces child's on filename conflict
- Child's unique rules are additive
- Child has full control when parent is absent

Use `memoryschema rules --conflicts` to see overridden rules.

For complete examples, API reference, and troubleshooting, see [docs/hierarchy-and-inheritance.md](hierarchy-and-inheritance.md).

## Full Specification

- **Schema:** `docs/schema.md` — the authoritative structural reference
- **Rules:** `.claude/rules/memory-schema.md` — derived from schema, auto-loaded
- **Guidelines:** `.claude/rules/memory-working.md`, `memory-corpus.md` — per-scope
- **CLI:** `memoryschema --help` — all operational commands
