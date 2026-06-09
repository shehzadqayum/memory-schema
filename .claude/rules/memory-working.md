# Working Memory Guidelines (importance: 10)

**Enforcement: strict — every response MUST end with a memory write to `memory/<name>.md`.** No exceptions. Non-compliance is a protocol violation.

---

## What to capture

The thinking, not just the conclusion. A future session should be able to reconstruct the reasoning path, not just the outcome.

- `<memory:prompt>` — what was asked
- `<memory:reasoning>` — why this approach, what alternatives, what connections
- `<memory:observation>` — specific facts and data

## How much

As many entities as the thinking requires. The entity is small by design — volume compensates.

## Importance

Working memory entities should use importance **7-10**:
- 10: critical decisions, architectural changes, user corrections
- 8-9: significant findings, evaluations, initiative records
- 7: routine session reasoning

## Type guidance

- `semantic` — facts, decisions, references (persist indefinitely)
- `episodic` — session events, debugging, implementation history (decays)
- `procedural` — validated approaches, user feedback, corrected behaviors (reinforced by access)

## File path

Write to `memory/<name>.md` where `<name>` is kebab-case and describes the content.

## Compact resilience

The PostToolUse hook automatically appends working memory entries to MEMORY.md. After a `/compact` event, all working memory remains visible in context via the MEMORY.md index.
