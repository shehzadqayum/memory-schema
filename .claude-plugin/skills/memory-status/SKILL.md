# /memory-status — Show memory system status

Display the current state of the memory store: backend type, node count, and embedding coverage.

## Usage

```
/memory-status
```

## When to use

To check the health and size of the memory system, or to verify that the store is accessible and populated.

## Procedure

1. Run the status command via Bash:

```bash
memoryschema status
```

2. For machine-readable output:

```bash
memoryschema status --json
```

## Output

Reports:
- **Backend** — which store implementation is active (JsonlStore or Neo4jStore)
- **Nodes** — total number of memory entities
- **Embedding coverage** — percentage of entries with vector embeddings
