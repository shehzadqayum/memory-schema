# Memory System — Technical Reference

## Overview

**Schema:** `docs/schema.md` (source of truth, v2)
**Guidelines:** `.claude/rules/memory-*.md` (per-scope usage)
**Embedding model:** Voyage AI `voyage-4-lite` (1024 dimensions)
**Primary store:** Neo4j (L2b, optional)
**Fallback store:** `memory/store.jsonl` (L1b)
**Access:** `get_store()` — Neo4j first, JSONL fallback
**CLI:** `memoryschema` (pip install memory-schema)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  L0: MEMORY.md (always in context, auto-updated by hook) │
├─────────────────────────────────────────────────────────┤
│  L1a: Markdown files (git-tracked, human-readable)       │
├─────────────────────────────────────────────────────────┤
│  L1b: JSONL store (structured, machine-readable)         │
├─────────────────────────────────────────────────────────┤
│  L2a: Voyage embeddings (1024-dim per entry)             │
├─────────────────────────────────────────────────────────┤
│  L2b: Neo4j (vector k-NN, graph traversal, associations) │
└─────────────────────────────────────────────────────────┘
```

Each layer adds capability without being required. The system degrades gracefully.

**Compact resilience:** The PostToolUse hook auto-appends working memory entries to MEMORY.md on write.

---

## Entity Structure (Schema v2)

```xml
<memory:entity schema="2" name="unique-identifier" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact</memory:observation>
  </memory:observations>
  <memory:prompt>User input that triggered this memory</memory:prompt>
  <memory:reasoning>Narrative thinking — why, alternatives, connections</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
  <memory:source>provenance</memory:source>
</memory:entity>
```

**Required:** schema, name, description.
**Optional:** importance (default 5), type (default semantic), observations, reasoning, prompt, relations, source, project.

---

## Type System

| Type | Use |
|------|-----|
| `semantic` | Facts, references, corpus content |
| `episodic` | Session events, decisions |
| `procedural` | Validated approaches, feedback |

---

## Retrieval

### Scoring Formula

```
score = recency(0.995^hours) × 0.2 + importance/10 × 0.3 + cosine_similarity × 0.5
```

Hub bonus: +0.05 per backlink (capped at 5).
Text match boost: +0.1 if query string found in name/description/observations/prompt/reasoning.

### Three-Channel Cascade

```
Vector k-NN seeds → explicit relations → backlinks → ASSOCIATED_WITH associations
```

---

## Pipeline

### Write Path

```
Response → memory entity (.md) → PostToolUse hook
  → parse (tags.py) → embed (Voyage AI) → Neo4j upsert (or JSONL fallback)
  → single-node associations → append to MEMORY.md (compact resilience)
```

### Recall Path

```
Query → embed query → vector k-NN seeds → cascade BFS
  → relations + backlinks + associations → ranked results
```

---

## Python API

```python
from memoryschema import (
    MemoryConfig, MemoryStore, get_store,
    parse_memory_file, parse_memory_content,
    validate, validate_file, validate_directory,
    discover_memory_files, consolidate,
)

# Optional (require extras)
from memoryschema import Neo4jMemoryStore, embed_text, embed_batch, rerank
```

### Key Classes

- `MemoryConfig` — configuration dataclass (env vars, paths, defaults)
- `MemoryStore` — JSONL-backed store (L1b)
- `Neo4jMemoryStore` — Neo4j-backed store (L2b, same interface)
- `get_store(config=None)` — factory, returns best available backend

---

## Scripts

| Module | Purpose |
|--------|---------|
| `memoryschema.tags` | Parse `<memory:entity>` XML (v2: prompt + reasoning) |
| `memoryschema.store` | JSONL store + `get_store()` factory |
| `memoryschema.neo4j_store` | Neo4j store (O(1) upsert, vector k-NN, graph) |
| `memoryschema.embeddings` | Voyage AI: embed_text, embed_batch, rerank |
| `memoryschema.validator` | Schema validation (V1-V10, R1-R5, F1-F3) |
| `memoryschema.schema` | Create Neo4j indexes and constraints |
| `memoryschema.consolidation` | Batch index un-indexed files |
| `memoryschema.migration` | JSONL ↔ Neo4j migration |
| `memoryschema.reembed` | Re-embed entries by prefix |
| `memoryschema.discovery` | Find .md files under a path |
| `memoryschema.config` | Centralized configuration + `from_toml()` factory |
| `memoryschema.hierarchy` | Dot-notation project hierarchy: `parse_project_path`, `parent_project`, `ancestor_projects`, `is_ancestor_of`, `is_descendant_of`, `project_matches_scope`, `project_matches_filter`, `validate_project_name` |
| `memoryschema.inheritance` | TOML config chain + rules resolution: `find_toml_config`, `load_toml_config`, `flatten_toml`, `walk_config_chain`, `resolve_config_chain`, `rules_ancestry`, `resolve_rules`, `overridden_rules`, `validate_toml_name` |

---

## Configuration

| Setting | Default | Env var |
|---------|---------|---------|
| Project name | `default` | `MEMORY_PROJECT` |
| Neo4j URI | `bolt://localhost:7687` | `NEO4J_URI` |
| Neo4j user | `neo4j` | `NEO4J_USER` |
| Neo4j password | `changeme` | `NEO4J_PASSWORD` |
| Voyage API key | (none) | `VOYAGE_API_KEY` |
| Embed model | `voyage-4-lite` | — |
| Embed dimensions | 1024 | — |
| Association k | 10 | — |
| Recency decay | 0.995^hours | — |

---

## Testing

### Coverage

390 tests across 25 files. 20/20 doctor checks. Target: 100% module coverage.

| Category | Test files | Tests |
|----------|-----------|------:|
| Core modules (config, discovery, validator, tags, store, consolidation) | 6 | 120 |
| Mocked external deps (embeddings, neo4j_store, schema, migration, reembed) | 5 | 46 |
| Lazy imports (__init__.py) | 1 | 23 |
| CLI commands (all 10 modules) | 10 | 73 |

### Mocking Patterns

| Dependency | Mock target | Pattern |
|-----------|-------------|---------|
| `voyageai.Client` | `memoryschema.embeddings.voyageai` | `patch("memoryschema.embeddings.voyageai")` — mock Client, embed, rerank returns |
| `neo4j.GraphDatabase` | `memoryschema.neo4j_store.GraphDatabase` | `patch("memoryschema.neo4j_store.GraphDatabase")` — mock driver, session, run |
| Docker CLI | `subprocess.run` | `patch("subprocess.run")` — mock container status, compose commands |
| Click CLI | `click.testing.CliRunner` | `runner.invoke(cli, ["command", "--flag"])` — test exit codes, output |
| File I/O | `tmp_path` fixture | pytest's built-in temp directory — real file ops, isolated |

### Diagnostics

`memoryschema doctor` — 18 live checks:

| Check | What | Fix on failure |
|-------|------|----------------|
| python | Python >= 3.10 | Upgrade |
| package | importable, version | Reinstall |
| config | MemoryConfig loads | Show missing env vars |
| memory_dir | memory/ exists | `memoryschema init` |
| memory_index | MEMORY.md exists | `memoryschema init` |
| rules | .claude/rules/memory-schema.md | `memoryschema init` |
| guidelines | scope guideline installed | `memoryschema init --scopes working` |
| store_jsonl | store.jsonl accessible | `memoryschema init` |
| docker | Docker installed | Install Docker |
| neo4j_container | container running | `memoryschema neo4j deploy` |
| neo4j_connection | Bolt connection | `memoryschema neo4j up` |
| neo4j_schema | indexes present | `memoryschema neo4j schema` |
| neo4j_nodes | node count > 0 | `memoryschema index` |
| voyage_key | API key set | `export VOYAGE_API_KEY=...` |
| voyage_embed | test embed succeeds | Check key validity |
| hook | registered | `memoryschema hook install` |
| hook_script | exists, executable | Reinstall package |
| tests | pytest passes | Fix failing tests |

---

## Design Principles

1. **Schema + guidelines = core** — schema is structure (reusable), guidelines are usage (per-scope)
2. **Graceful degradation** — five layers, each independent
3. **Source of truth** — `docs/schema.md` is authoritative
4. **Importance-correlated enforcement** — 8-10 strict, 4-7 standard, 1-3 advisory
5. **Thin schema, rich guidelines** — 3 required fields, everything else optional
