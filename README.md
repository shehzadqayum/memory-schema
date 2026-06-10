# memory-schema

XML-based memory entity system with JSONL/Neo4j storage, Voyage AI embeddings, hierarchical agent nesting, and Claude Code integration.

## Quickstart

```bash
pip install memory-schema[all]
cd ~/Projects/my-project
memoryschema init --project my-project --scopes working --with-neo4j
memoryschema hook install
export VOYAGE_API_KEY=voy-xxxxx
memoryschema status
```

Done. Claude Code will now selectively write memory entities when decisions, corrections, or novel facts are established.

---

## Install

```bash
# Minimal (JSONL store, no embeddings, no Neo4j)
pip install memory-schema

# With Neo4j graph store
pip install memory-schema[neo4j]

# With Voyage AI embeddings
pip install memory-schema[embeddings]

# Everything
pip install memory-schema[all]

# Development
pip install memory-schema[all,dev]
```

**Dependencies:**
- `click` — CLI framework (always installed)
- `neo4j` — Neo4j Python driver (optional: `[neo4j]`)
- `voyageai` — Voyage AI embeddings API (optional: `[embeddings]`)
- `numpy` — vectorized scoring (optional: `[numpy]`, graceful fallback to pure Python)

---

## Initialize Project

```bash
memoryschema init --project my-project --scopes working,corpus --with-neo4j
```

Creates:
```
my-project/
├── memory/
│   └── MEMORY.md                      # L0 index (auto-loaded by Claude Code)
├── docker-compose.yml                 # Neo4j container config
├── .env.example                       # Environment variable reference
└── .claude/rules/
    ├── memory-schema.md               # Schema rules (auto-loaded)
    ├── memory-working.md              # Working memory guidelines (selective write)
    └── memory-corpus.md               # Corpus guidelines (importance 4-7)
```

### Without Neo4j (JSONL only)

```bash
memoryschema init --project my-project --scopes working
```

Works immediately. Add Neo4j later with `memoryschema neo4j deploy`.

### TOML Configuration

`memoryschema init` generates a `memoryschema.toml` config file. For nested agents, config inherits upward — parent TOML values override child on conflict:

```bash
# Parent agent
memoryschema --project org init

# Child agent (inside parent)
cd projects/team-alpha
memoryschema --project org.team-alpha init

# Inspect inheritance
memoryschema config --chain
memoryschema rules --conflicts
```

---

## Register Hook

```bash
memoryschema hook install
```

Adds the PostToolUse Write hook to `~/.claude/settings.json`. The hook:
1. Fires on every Write to `memory/*.md`
2. Parses the `<memory:entity>` XML
3. Embeds via Voyage AI (if key set)
4. Indexes to Neo4j (primary) or JSONL (fallback)
5. Appends to MEMORY.md (compact resilience)

---

## Configure Voyage AI

```bash
export VOYAGE_API_KEY=voy-xxxxx
memoryschema voyage status
```

Get your key at [dash.voyageai.com](https://dash.voyageai.com/).

Without a key, the system works but without semantic search — structured queries only.

---

## Verify Deployment

```bash
memoryschema status
```

Output:
```
Backend: Neo4jMemoryStore
Nodes:   0
Store:   /path/to/memory/store.jsonl
URI:     bolt://localhost:7687
```

---

## First Memory

Write a memory file:

```xml
<memory:entity schema="3" name="first-memory" type="semantic" importance="7">
  <memory:description>My first memory entity</memory:description>
  <memory:reasoning>Testing the memory system</memory:reasoning>
</memory:entity>
```

Index it:
```bash
memoryschema write memory/first-memory.md
```

Query it:
```bash
memoryschema recall "first memory"
```

---

## Graceful Degradation

Each external service is optional. The system degrades gracefully:

| Without | Impact | How to add later |
|---------|--------|-----------------|
| Neo4j | JSONL store (slower for large datasets) | `memoryschema neo4j deploy` + `memoryschema migrate jsonl-to-neo4j` |
| Voyage AI | No semantic search (keyword only) | `export VOYAGE_API_KEY=...` + `memoryschema embed --all` |
| Docker | No Neo4j (JSONL only) | Install Docker, then `memoryschema neo4j deploy` |
| Claude Code | No auto-indexing (manual `memoryschema write`) | Install Claude Code, `memoryschema hook install` |

---

## CLI Reference

### Setup
| Command | Description |
|---------|-------------|
| `memoryschema init` | Initialize project (memory dir, docker-compose, rules) |
| `memoryschema neo4j deploy` | Full Neo4j deployment (pull, start, schema, verify) |
| `memoryschema neo4j up/down` | Start/stop Neo4j container |
| `memoryschema neo4j status` | Container state, connectivity, node count |
| `memoryschema neo4j schema` | Create/verify indexes (idempotent) |
| `memoryschema neo4j reset --confirm` | Drop all data, recreate schema |
| `memoryschema neo4j logs` | Stream container logs |
| `memoryschema neo4j shell` | Open Cypher shell |
| `memoryschema voyage status` | Check API key, test embed |
| `memoryschema voyage test <text>` | Embed text, show vector stats |
| `memoryschema hook install` | Register PostToolUse hook |
| `memoryschema hook status` | Show hook registration |

### Operations
| Command | Description |
|---------|-------------|
| `memoryschema status` | Backend, node count, store path |
| `memoryschema recall <query> [--project]` | Semantic search with cascade (scoped to hierarchy) |
| `memoryschema get <name>` | Retrieve single entity |
| `memoryschema list` | List entities with filters |
| `memoryschema write <file>` | Parse, validate, embed, index |
| `memoryschema delete <name> --confirm` | Remove entity |
| `memoryschema search <text> [--project]` | Keyword search (scoped to subtree) |
| `memoryschema validate [path]` | Schema validation |

### Indexing
| Command | Description |
|---------|-------------|
| `memoryschema index` | Batch index un-indexed files |
| `memoryschema embed --prefix/--all` | Re-embed entries |
| `memoryschema embed --coverage` | Embedding coverage stats |
| `memoryschema associations` | Show/recompute k-NN |

### Data
| Command | Description |
|---------|-------------|
| `memoryschema migrate jsonl-to-neo4j` | JSONL to Neo4j |
| `memoryschema migrate neo4j-to-jsonl` | Neo4j to JSONL |
| `memoryschema sync` | Reconcile stores |
| `memoryschema backup` | Full or selective backup |
| `memoryschema restore <archive>` | Restore from backup |
| `memoryschema reset --confirm` | Wipe data |
| `memoryschema clean --confirm` | Complete removal |
| `memoryschema export` | Portable archive |
| `memoryschema import <source>` | Import from archive |

### Diagnostics & Inheritance
| Command | Description |
|---------|-------------|
| `memoryschema doctor` | 21-point health check (includes TOML + rules inheritance) |
| `memoryschema rules` | Show effective rules with inheritance markers |
| `memoryschema rules --conflicts` | Show child rules overridden by parent |
| `memoryschema config` | Show effective config |
| `memoryschema config --chain` | Show config inheritance chain with sources |

All query commands support `--json` for agent consumption. All destructive commands require `--confirm`.

---

## Architecture

**Source of truth:** `docs/schema.md` — the memory schema document.

**Delivery:** Schema rules deploy to `.claude/rules/memory-schema.md` (auto-loaded, no CLAUDE.md conflict).

**Enforcement:** Correlates with importance attribute (1-10):
- **8-10** (working memory): selective — write on decisions, corrections, novel facts
- **4-7** (corpus): standard — batch ingested
- **1-3** (advisory): write when significant

**Storage:** 5 layers with graceful degradation:
```
L0: MEMORY.md → L1a: Markdown files → L1b: JSONL → L2a: Embeddings → L2b: Neo4j
```

**Hierarchical Inheritance:** Projects nest as agents via dot-notation (`parent.child`). Parent's config and rules override child's on conflict. Config via `memoryschema.toml` files with upward chain walking. CLI > env vars > parent TOML > child TOML > defaults. See `docs/system-overview.md` for details.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `memoryschema: command not found` | Not installed or not on PATH | `pip install memory-schema` |
| Neo4j connection refused | Container not running | `memoryschema neo4j up` |
| No semantic search results | VOYAGE_API_KEY not set | `export VOYAGE_API_KEY=voy-xxxxx` |
| Hook not firing | Not registered | `memoryschema hook install` |
| `ImportError: neo4j` | Optional dep not installed | `pip install memory-schema[neo4j]` |
| `ImportError: voyageai` | Optional dep not installed | `pip install memory-schema[embeddings]` |
| Schema validation errors | Invalid entity XML | `memoryschema validate memory/file.md` |
| MEMORY.md not updating | Hook timeout or failure | Check `memoryschema hook status` |

---

## Testing

```bash
# Install dev dependencies
pip install memory-schema[all,dev]

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=memoryschema --cov-report=term-missing

# Run specific test file
pytest tests/test_store.py -v
```

**472 tests** across 27 test files covering all modules:

| Category | Files | Tests | What's tested |
|----------|------:|------:|---------------|
| Core modules | 7 | 236 | config, discovery, validator, tags, store, consolidation, hierarchy |
| Mocked deps | 5 | 48 | embeddings, neo4j_store, schema, migration, reembed |
| Lazy imports | 1 | 23 | __init__.py public API, __getattr__, __all__ |
| CLI commands | 12 | 89 | All CLI modules via Click CliRunner |
| Integration | 2 | 76 | inheritance (config chain), write_gate, eval harness |

**Mocking strategy:** External dependencies (voyageai, neo4j, Docker) are mocked with `unittest.mock.patch` — no real API calls, containers, or network required to run tests.

**Diagnostics:** `memoryschema doctor` runs 21 health checks against the live system. Use it to verify a real deployment:

```bash
memoryschema doctor          # Human-readable status report
memoryschema doctor --json   # Machine-readable for agents
memoryschema doctor --fix    # Auto-remediation suggestions
```

---

## Documentation

- `docs/schema.md` — Memory schema specification (source of truth)
- `docs/hierarchy-and-inheritance.md` — Agent hierarchy and config/rules inheritance reference
- `docs/implementation-guide.md` — Step-by-step deployment guide
- `docs/system-overview.md` — Conceptual overview
- `docs/technical-reference.md` — Architecture, API, configuration

---

## License

MIT
