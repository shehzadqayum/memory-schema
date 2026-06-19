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

Every session has ONE active chain entity that accumulates reasoning steps. This is the primary memory mechanism.

### Lifecycle

1. **Start** — `memoryschema chain start <name>` authorises the entity for writes. Create the memory file on first response.
2. **Update** — on every subsequent response, UPSERT the same chain entity (authorised = writable). All other memories are read-only (unauthorised).
3. **Release** — `memoryschema chain release` makes it read-only permanently. Append a "Conclusion:" observation before releasing.
4. **New chain** — only one chain authorised at a time. Release first, then start a new one.

After release, all memories are read-only until a new chain is started. The active chain name is stored in `memory/.active_chain`.

### How to update

**Edit** (not Write) the SAME `memory/<chain-name>.md` file on every response.
NEVER use Write on an existing chain file — it replaces the entire file, risking observation loss.

Three targeted Edits per update:
1. **Append** new `<memory:observation>` before `</memory:observations>`
2. **Replace** `<memory:description>` content
3. **Append** to `<memory:reasoning>` — add new narrative after a `---` separator, preserving prior reasoning

The upsert semantics at the index layer handle accumulation (only works because the chain is authorised):
- Observations are APPENDED (each step adds to the list)
- Description is REPLACED (summary evolves)
- Reasoning is REPLACED (narrative updated with latest thinking)
- Relations are MERGED (USES links to evidence accumulate)
- Embedding is re-computed on every Write or Edit (stays current as chain grows)

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

Standalone memories are immediately read-only after write (unauthorised). They should be linked from the chain via USES relations.

---

## What to capture

The thinking, not just the conclusion. A future session should be able to reconstruct the reasoning path, not just the outcome.

- `<memory:prompt>` — what was asked (set on chain creation)
- `<memory:reasoning>` — why this approach, what alternatives, what connections (updated each step)
- `<memory:observation>` — "Step N: <specific facts and actions>"
- `<memory:chain>` — reasoning chain context: what investigation this memory belongs to (same text for all memories in the same chain — enables clustering via chain-space similarity)

## Importance

Importance means **salience** — how important this memory is for future sessions. Use the full 1-10 range:

| Range | Use for |
|-------|---------|
| 8-10 | Critical decisions, user corrections, architectural choices |
| 5-7 | Standard working knowledge, implementation details |
| 1-4 | Transient observations, session-specific context |

Scope (which project sees a memory) is handled by the `project` field, not importance.

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
