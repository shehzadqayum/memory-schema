# /recall — Search memories

Semantic search across the memory store. Returns the most relevant memories for a query, using 7-space variance-weighted retrieval.

## Usage

```
/recall <query>
```

## When to use

Use this skill before answering user questions to surface relevant prior knowledge. The memory system captures context across sessions — recall closes the loop by retrieving it.

Skip recall only for purely mechanical operations (git commits, file staging) where no prior knowledge is relevant.

## Procedure

### 1. Search project store (primary)

```bash
memoryschema recall "<query>" --limit 3
```

### 2. Search user-level store (cross-project knowledge)

If the current project has its own `memory/` directory (not `~/.claude/memory/`), also search the user-level store for cross-project knowledge:

```bash
memoryschema --root ~/.claude recall "<query>" --limit 3
```

Skip this step if the project root IS `~/.claude` (same store — no need to search twice).

### 3. Merge results

- Project results take priority (shown first)
- User-level results provide cross-project context
- Deduplicate by name if the same entry appears in both
- Use the combined context to inform the response

## Options

- `--limit N` — number of results (default 3)
- `--project NAME` — scope to a project hierarchy
- `--include-inactive` — include superseded/archived entries
- `--json` — output as JSON for programmatic use

## Examples

```bash
# Project-level search
memoryschema recall "how does the hook pipeline work" --limit 3

# User-level cross-project search
memoryschema --root ~/.claude recall "debugging patterns" --limit 3

# Scoped to a project hierarchy
memoryschema recall "auth flow" --project ict.auth --limit 5
```
