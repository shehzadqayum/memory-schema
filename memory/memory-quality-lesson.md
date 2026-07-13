---
schema: 5
type: procedural
importance: 9
---

Write facts, decisions, and patterns as semantic/procedural — not session narration as episodic

## Observations

- Session-close and commit-log memories are low-value episodic metadata that don't cluster or recall well
- High-value memories extract the knowledge: what was learned, what pattern was validated, what fact was established
- A single working session can produce 5+ semantic/procedural memories from decisions and discoveries
- The type field drives scoring: semantic persists (recency floor 0.6), procedural reinforces with use, episodic decays

## Reasoning

The corpus was 23/40 episodic, mostly session-close entries. These are commit logs, not knowledge. The user's correction highlights that the LLM should use its judgment to classify and extract — writing 'fixed hook quoting bug' as episodic is waste; writing 'never use double-quoted dict keys in bash python3 -c blocks' as procedural is knowledge that prevents future bugs.

## Prompt

User pointed out that I was writing lazy episodic metadata instead of extracting actual knowledge

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
