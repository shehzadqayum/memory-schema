# Working Memory Guidelines

**Enforcement: MANDATORY — maintain an active chain entity throughout every session.**

## Active Chain

Every session has ONE active chain entity that accumulates reasoning steps. This is the primary memory mechanism.

### Lifecycle

1. **Create** — on first response, if no active chain exists, create `memory/chain-<topic>.md` with Step 1 as an observation
2. **Update** — on every subsequent response, UPSERT the same chain entity: append a new step observation, update description (evolving summary) and reasoning (current narrative)
3. **Release** — at session end or topic change, append a "Conclusion:" observation and finalize the description/reasoning. The chain becomes a permanent record.
4. **New chain** — if the topic changes significantly mid-session, release the current chain and create a new one

### How to update

Write the SAME `memory/chain-<topic>.md` file on every response. The upsert semantics handle accumulation:
- Observations are APPENDED (each step adds to the list)
- Description is REPLACED (summary evolves)
- Reasoning is REPLACED (narrative updated with latest thinking)
- Relations are MERGED (USES links to evidence accumulate)
- Embedding is re-computed on every write (stays current as chain grows)

### What each step captures

- `<memory:observation>` — "Step N: <what happened in this response>"
- `<memory:description>` — updated one-line summary of the chain so far
- `<memory:reasoning>` — updated narrative connecting all steps so far
- `<memory:prompt>` — the original trigger question (set on create, kept on updates)
- `<memory:relations>` — USES links to any evidence memories referenced

### Additional standalone memories

The active chain is the default. Additionally write standalone memories when:
- A durable fact is established (semantic — persists beyond the chain)
- A reusable pattern is validated (procedural — reinforced by access)
- A critical decision or correction occurs (high importance, standalone)

These standalone memories should be linked from the chain via USES relations.

---

## What to capture

The thinking, not just the conclusion. A future session should be able to reconstruct the reasoning path, not just the outcome.

- `<memory:prompt>` — what was asked (set on chain creation)
- `<memory:reasoning>` — why this approach, what alternatives, what connections (updated each step)
- `<memory:observation>` — "Step N: <specific facts and actions>"

## Importance

Importance means **salience** — how important this memory is for future sessions. Use the full 1-10 range:

| Range | Use for |
|-------|---------|
| 8-10 | Critical decisions, user corrections, architectural choices |
| 5-7 | Standard working knowledge, implementation details |
| 1-4 | Transient observations, session-specific context |

Scope (which project sees a memory) is handled by the `project` field, not importance.

## Type guidance

- `semantic` — facts, decisions, references (persist indefinitely)
- `episodic` — session events, debugging, implementation history (decays)
- `procedural` — validated approaches, user feedback, corrected behaviors (reinforced by access)

## File path

Write to `memory/<name>.md` where `<name>` is kebab-case and describes the content.

## Chain entities

After multi-step reasoning, create a **chain entity** (see Rule 9 in memory-schema.md) that captures the full sequence from trigger to conclusion. Chain entities:

- Distill episodic steps into a persistent semantic summary
- Link to evidence via USES relations (cascade brings in details on recall)
- Are named with `chain-` prefix for discoverability
- Should be created when: an investigation concludes, an experiment produces results, debugging resolves an issue, or a design decision is reached through alternatives

Prefer one chain entity over multiple disconnected episodic memories when the reasoning forms a coherent sequence.

## Compact resilience

The PostToolUse hook automatically appends working memory entries to MEMORY.md. After a `/compact` event, all working memory remains visible in context via the MEMORY.md index. L0 budget enforcement evicts lowest-scoring entries when the index exceeds the configured token limit.
