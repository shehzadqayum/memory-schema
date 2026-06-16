# /chain-status — Show active chain

Check which chain entity is currently authorised for writes, or confirm that all memories are read-only.

## Usage

```
/chain-status
```

## When to use

When you need to check whether a chain is active before writing memories, or to confirm the current session's chain state.

## Procedure

1. Run the chain status command via Bash:

```bash
memoryschema chain status
```

2. Output is one of:
   - `Active chain: <name>` — this chain accepts upserts
   - `No active chain (all memories read-only)` — start a chain first to enable writes
