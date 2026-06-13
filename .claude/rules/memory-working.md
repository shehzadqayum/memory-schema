# Working Memory Guidelines

**Enforcement: MANDATORY — write a memory entity on every response (testing mode).**

Write a `memory/<name>.md` entity file on EVERY response. The PostToolUse hook will parse, embed (via Voyage AI), gate-check, and index it automatically. This ensures the full write pipeline (parse → embed → gate → store → MEMORY.md) is exercised continuously.

The entity MUST contain at minimum: name, description, and one observation capturing what happened in the response. Use your judgement for type and importance.

---

## What to capture

The thinking, not just the conclusion. A future session should be able to reconstruct the reasoning path, not just the outcome.

- `<memory:prompt>` — what was asked
- `<memory:reasoning>` — why this approach, what alternatives, what connections
- `<memory:observation>` — specific facts and data

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

## Write decline instrumentation

When the selective-write policy above is weighed and the decision is **not** to write, record a decline:

```bash
memoryschema decline --reason "mechanical test output, no novel fact"
```

**Limitation:** declines instrument only *considered* candidates — cases where the write was actively weighed and rejected. Candidates never considered are invisible by construction. The decline data must not be over-read as complete coverage of non-write decisions.

## Compact resilience

The PostToolUse hook automatically appends working memory entries to MEMORY.md. After a `/compact` event, all working memory remains visible in context via the MEMORY.md index. L0 budget enforcement evicts lowest-scoring entries when the index exceeds the configured token limit.
