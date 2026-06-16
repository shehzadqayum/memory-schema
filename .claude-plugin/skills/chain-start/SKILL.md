# /chain-start — Start a reasoning chain

Authorise a new chain entity for writes. Only one chain can be active at a time. All other memories remain read-only.

## Usage

```
/chain-start <name>
```

## When to use

At the beginning of a session or investigation when you need a live accumulating memory. The chain entity captures reasoning steps across responses.

## Procedure

1. Run the chain start command via Bash:

```bash
memoryschema chain start "<name>"
```

2. If successful, create the chain's memory file at `memory/<name>.md` on first response
3. If a chain is already active, the command will error — release the existing chain first with `/chain-release`

## Naming convention

Use `chain-` prefix with a descriptive kebab-case name:
- `chain-debugging-auth-issue`
- `chain-designing-plugin-architecture`
- `chain-evaluating-scoring-weights`

## Example

```bash
memoryschema chain start "chain-investigating-recall-performance"
```

Output: `Chain started: chain-investigating-recall-performance (authorised for writes)`
