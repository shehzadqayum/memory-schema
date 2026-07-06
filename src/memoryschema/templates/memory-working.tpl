# Working Memory Guidelines

**Enforcement: MANDATORY — recall before every response, write after.**

## Recall Before Responding

Before answering ANY user question, recall relevant memories:

```bash
memoryschema recall "<user's question or topic>" --limit 3
```

Use the recalled memories as context for your response. If a recalled memory directly answers the question, cite it. If recalled memories provide background, use them to inform your answer. Call `memoryschema recall` via the Bash tool — this is a real retrieval operation, not file reading.

**Why:** The memory system captures knowledge across sessions. Without recall, that knowledge is write-only — captured but never used. Recall closes the loop.

**When to skip:** Only skip recall for purely mechanical operations (git commits, file staging) where no prior knowledge is relevant.

## Active Chain

Every session has ONE active chain entity that accumulates reasoning steps. This is the primary memory mechanism. The active chain name is stored in `memory/.active_chain`.

### Lifecycle

1. **Start** — `memoryschema chain start <name>` authorises the name (only one chain at a time; kebab-case, `chain-` prefix).
2. **Step** — after each substantive response, record what happened via the CLI (below). The first step bootstraps the file.
3. **Release** — conclude with a `Conclusion:` step, then `memoryschema chain release`; immediately `chain start` a successor (the store should never sit without an active chain).

### How to update — the deterministic write path

```bash
memoryschema chain step --stdin [--desc "evolving summary"] [--reasoning TEXT] [--uses <evidence-memory>] <<'EOF'
What happened, decisions, results. Raw < > & are SAFE here — code does the structuring.
EOF
```

Plain text in; code auto-numbers the step, validates the file round-trip, indexes to both stores, and rebuilds the MEMORY.md index. `--desc` replaces the evolving summary; `--reasoning` appends narrative after a `---` separator; `--uses` links evidence (and logs a citation).

**Do NOT hand-edit the chain file as the normal path.** Hand-editing `memory/*.md` is the fallback only (the PostToolUse hook indexes it, but hand-authored structure caused store corruption historically — the CLI path makes that impossible). If you must hand-edit, use Edit (not Write) and check `memoryschema sync` after.

### Standalone memories — durable facts

```bash
memoryschema remember <kebab-name> --desc "<one line, <=120 chars>" \
  --obs "atomic fact" [--obs "..."] [--uses <target>] [--supersedes <outdated>] \
  [--key DOMAIN.fact] [--importance N]
```

Write standalone memories when: a durable fact is established (semantic), a reusable pattern is validated (procedural), or a critical decision/correction occurs. `--key` gives a fact identity — a later `remember` with the same key deterministically supersedes the old holder (point-in-time recall via `recall --as-of`). Standalone memories are read-only after creation; link them from the chain via `--uses`.

## What to capture

The thinking, not just the conclusion. A future session should be able to reconstruct the reasoning path, not just the outcome: what was asked (prompt), why this approach and what alternatives (reasoning), specific facts and actions (observations/steps), and what investigation it belongs to (chain context).

## Importance

Importance means **salience** — how important this memory is for future sessions. Use the full 1-10 range (the write gate nudges you if you always pick the store's mode):

| Range | Use for |
|-------|---------|
| 8-10 | Critical decisions, user corrections, architectural choices |
| 5-7 | Standard working knowledge, implementation details |
| 1-4 | Transient observations, session-specific context |

Scope (which project sees a memory) is handled by the `project` field, not importance.

## Health

`memoryschema preflight` (dependency gate) · `sync` (read-only drift report) · `reconcile` (heals all layers to the `memory/*.md` set). Run `sync` if anything looks inconsistent.

## Compact resilience

The write path and hook REGENERATE `MEMORY.md` as a token-budgeted index of the active set on every write. After a `/compact` event, working memory stays visible via that index; lowest-importance entries are dropped first when over budget (the header says how many).
