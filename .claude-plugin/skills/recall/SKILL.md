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

1. Run the recall command via Bash:

```bash
memoryschema recall "<query>" --limit 3
```

2. Use the returned memories as context for your response:
   - If a memory directly answers the question, cite it
   - If memories provide background, use them to inform the answer
   - If no relevant memories are found, proceed without

## Options

- `--limit N` — number of results (default 3)
- `--project NAME` — scope to a project hierarchy
- `--include-inactive` — include superseded/archived entries
- `--json` — output as JSON for programmatic use

## Examples

```bash
memoryschema recall "how does the hook pipeline work" --limit 3
memoryschema recall "auth flow" --project ict.auth --limit 5
memoryschema recall "chain entity lifecycle" --json
```
