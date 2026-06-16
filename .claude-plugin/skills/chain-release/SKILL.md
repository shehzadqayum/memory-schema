# /chain-release — Release the active chain

Make the active chain entity read-only permanently. After release, all memories are read-only until a new chain is started.

## Usage

```
/chain-release
```

## When to use

When an investigation or session concludes and the chain's reasoning is complete. Always append a "Conclusion:" observation to the chain before releasing.

## Procedure

1. Write a final update to the chain entity with a "Conclusion:" observation
2. Run the chain release command via Bash:

```bash
memoryschema chain release
```

3. Output is one of:
   - `Chain released: <name> (now read-only)` — success
   - `No active chain to release` — nothing to do

## Important

- Append "Conclusion: ..." as the final observation before releasing
- After release, the chain entity is permanently read-only
- Start a new chain with `/chain-start` for the next investigation
