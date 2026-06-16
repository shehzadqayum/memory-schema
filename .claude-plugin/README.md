# memory-schema plugin for Claude Code

Content-agnostic memory system with 7-space embedding and variance-weighted retrieval. This plugin provides hooks, rules, and skills — it wraps the `memory-schema` Python package (installed separately via pip).

## Prerequisites

```bash
pip install memory-schema[all]
```

The plugin does not bundle the source code. It calls the pip-installed `memoryschema` package via the hook and CLI commands. Without the package installed, the hook and skills will not function.

## Installation

### From local development checkout

```bash
# Clone the repo and install in editable mode
git clone <repo-url> memory-schema
cd memory-schema
pip install -e .[all,dev]

# The plugin directory is at .claude-plugin/ — point Claude Code to it
```

### Environment

```bash
# Required for semantic search (optional — degrades to keyword search without it)
export VOYAGE_API_KEY=voy-xxxxx
```

Get your key at [dash.voyageai.com](https://dash.voyageai.com/).

## What the plugin provides

### Hook: PostToolUse Write

Fires on every Write to `memory/*.md`. The hook:

1. Parses the `<memory:entity>` XML
2. Checks authorisation (only the active chain or new entities can be written)
3. Embeds across 7 spaces (default, name, description, observations, prompt, reasoning, chain)
4. Computes divergence profile (per-space distance from default)
5. Runs the write gate (validation, consistency, numeric probe, L0 echo)
6. Indexes to Neo4j (primary) or JSONL (fallback)
7. Updates MEMORY.md with L0 budget enforcement

### Rules

- **memory-schema.md** — Schema rules (entity structure, fields, relations, scoring, storage)
- **memory-working.md** — Working memory guidelines (recall before responding, chain lifecycle)

### Skills

| Skill | Description |
|-------|-------------|
| `/recall <query>` | Semantic search with dual-store support (project + user-level) |
| `/chain-start <name>` | Start a reasoning chain (authorise for writes) |
| `/chain-status` | Show the active chain |
| `/chain-release` | Release the active chain (make read-only) |
| `/memory-status` | Show store backend, node count, embedding coverage |

## Architecture

```
Plugin (.claude-plugin/)               Python package (pip-installed)
─────────────────────────              ────────────────────────────────
hooks/hooks.json  ──calls──>           hook-post-write.sh ──imports──> memoryschema.*
hooks/hook-post-write.sh               (tags, store, embeddings, write_gate, etc.)
rules/*.md        ──loaded──> prompt
skills/*.md       ──invoke──>          memoryschema CLI (recall, chain, status)

Data (hybrid scope)
───────────────────
Project: memory/store.jsonl, *.md      (project-specific memories)
User:    ~/.claude/memory/store.jsonl   (cross-project knowledge, fallback)
```

## Hybrid memory scope

The plugin supports both project-level and user-level memory:

- **Project store**: `memory/` directory in the project root — isolated per project
- **User store**: `~/.claude/memory/` — cross-project knowledge, used as fallback

The hook writes to whichever store the file path resolves to. If no project `memory/` directory can be derived from the path, it falls back to `~/.claude/memory/`.

The `/recall` skill searches the project store first, then the user-level store for cross-project context.

## Quick start

1. Install the package: `pip install memory-schema[all]`
2. Initialize a project: `memoryschema init --project my-project --scopes working`
3. Set your Voyage key: `export VOYAGE_API_KEY=voy-xxxxx`
4. Write a memory — Claude will auto-index it via the hook
5. Use `/recall` to search memories
6. Use `/chain-start` to begin a reasoning chain
