# Memory System — Implementation Guide

How to deploy the memory system in a new project using the `memory-schema` package.

## Prerequisites

- Python 3.11+
- Docker (optional, for Neo4j L2b)
- Voyage AI API key (optional, for embeddings L2a)
- Claude Code (optional, for hook integration)

## Step 1: Install

```bash
# Minimal (JSONL store only, no embeddings, no Neo4j)
pip install memory-schema

# With Neo4j support
pip install memory-schema[neo4j]

# With Voyage AI embeddings
pip install memory-schema[embeddings]

# Everything
pip install memory-schema[all]
```

## Step 2: Initialize Project

```bash
cd ~/Projects/my-project
memoryschema init --project my-project --scopes working
```

This creates:
- `memory/MEMORY.md` — L0 always-in-context index
- `docker-compose.yml` — Neo4j container config
- `.env.example` — environment variable reference
- `.claude/rules/memory-schema.md` — schema rules (auto-loaded by Claude Code)
- `.claude/rules/memory-working.md` — working memory guidelines (importance 10)

## Step 3: Deploy Neo4j (Optional)

```bash
memoryschema neo4j deploy
```

This pulls the Neo4j image, starts the container, waits for health, creates indexes, and verifies connectivity. One command.

Or manually:
```bash
docker compose up -d
memoryschema neo4j schema
memoryschema neo4j status
```

## Step 4: Configure Voyage AI (Optional)

```bash
export VOYAGE_API_KEY=voy-xxxxx
memoryschema voyage status
```

## Step 5: Register Hook

```bash
memoryschema hook install
```

This adds the PostToolUse Write hook to `~/.claude/settings.json` (global). The hook fires on every Write to `memory/*.md`, parsing, embedding, and indexing automatically.

**Note:** The hook installs globally, not per-project. On multi-project machines, the hook runs for all projects. This is safe — the hook derives the project root from the file path and only processes files under `memory/`.

## Step 6: Verify

```bash
memoryschema status
```

Should show: backend type, node count (0 for fresh install), store path.

## Step 7: Start Using

Open Claude Code in your project. The `.claude/rules/` files auto-load:
- `memory-schema.md` — structural rules for valid entities
- `memory-working.md` — selective write policy (write on decisions, corrections, novel facts)

Selected responses write a `<memory:entity>` to `memory/<name>.md` (per scope guidelines). The hook indexes it.

## Architecture

### Source of Truth

`docs/schema.md` in the package. The rules file (`.claude/rules/memory-schema.md`) is derived from it. On divergence, `docs/schema.md` wins.

### Storage Layers

| Layer | Store | On failure |
|-------|-------|------------|
| L0 | MEMORY.md | Never fails (always in context) |
| L1a | Markdown files | Never fails (git-tracked) |
| L1b | JSONL (store.jsonl) | Never fails (stdlib Python) |
| L2a | Voyage embeddings | Degrades to L1 (text search) |
| L2b | Neo4j | Degrades to L2a (JSONL + numpy) |

### Enforcement

Correlates with importance:
- **Importance 8-10** (working memory): selective — write on decisions, corrections, novel facts
- **Importance 4-7** (corpus): standard — batch imported
- **Importance 1-3** (advisory): write when significant

### CLI Reference

```
memoryschema init              # Project setup
memoryschema status            # Store health
memoryschema recall <query>    # Semantic search
memoryschema validate          # Schema validation
memoryschema neo4j deploy      # Full Neo4j setup
memoryschema neo4j status      # Container health
memoryschema voyage status     # API verification
memoryschema hook install      # Register hook
memoryschema backup            # Full backup
memoryschema export            # Portable archive
```

Run `memoryschema --help` for the complete command list.

## Verification & Testing

### Run diagnostics

```bash
memoryschema doctor
```

Checks 21 components: Python, package, config, filesystem, TOML, rules inheritance, Docker, Neo4j, Voyage, hook, tests. Each failure shows the cause and the exact fix command.

### Run tests

```bash
pip install memory-schema[all,dev]
pytest tests/ -v --cov=memoryschema
```

569 tests, 33 files. External dependencies are mocked — no Docker or API keys needed to run tests.

### Write tests for custom ingest scripts

```python
from memoryschema import MemoryStore, parse_memory_content, validate

def test_my_entity():
    content = '<memory:entity schema="3" name="test"><memory:description>Test</memory:description></memory:entity>'
    result = parse_memory_content(content)
    assert result['name'] == 'test'
    errors = validate(content)
    assert errors == []
```

## Adapting for a New Project

1. `pip install memory-schema[all]`
2. `memoryschema init --project <name> --scopes working --with-neo4j`
3. `memoryschema hook install`
4. `export VOYAGE_API_KEY=...`
5. `memoryschema doctor` — verify everything
6. Start Claude Code

The schema is the same across all projects. Only the guidelines change.

## TOML Configuration

`memoryschema init` generates a `memoryschema.toml` file:

```toml
[project]
name = "my-project"

[neo4j]
uri = "bolt://localhost:7687"

[retrieval]
recall_depth = 2
```

Config inherits upward — parent TOML values override child on conflict. CLI flags have highest priority, followed by environment variables, then TOML.

## Nested Agent Setup

```bash
# Parent agent
memoryschema --project org init --with-neo4j

# Child agent (inside parent directory)
cd projects/team-alpha
memoryschema --project org.team-alpha init
```

Verify inheritance:

```bash
memoryschema config --chain     # shows config sources
memoryschema rules --conflicts  # shows overridden rules
```

For detailed config resolution examples and troubleshooting, see [hierarchy-and-inheritance.md](hierarchy-and-inheritance.md).
