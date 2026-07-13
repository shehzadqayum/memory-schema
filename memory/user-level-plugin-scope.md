---
schema: 5
importance: 8
status: archived
---

User-level plugin: 3 models — per-project data, shared user memory, or hybrid (recommend hybrid)

## Observations

- Model A (per-project): plugin at ~/.claude/plugins/, data at each project's memory/ — complete isolation
- Model B (shared): all memories at ~/.claude/memory/ — cross-project knowledge but no isolation
- Model C (hybrid): project memory/ if exists + ~/.claude/memory/ fallback — project isolation + shared knowledge
- Hybrid rule: hook writes to project memory/ if exists, else ~/.claude/memory/. Recall searches project first, user fallback.
- User-level store becomes cross-project knowledge: debugging patterns, tool usage, preferences, decisions
- The project field already supports this — it tags origin for scoping at recall time

## Reasoning

The key question is data locality, not mechanism locality. The plugin (hooks, rules, skills) should be user-level for universal availability. The data needs a dual-scope model: project-specific memories for isolation, user-level memories for cross-project knowledge. The project field provides the logical scoping; the file system provides the physical scoping. Hybrid (Model C) gets both benefits with a simple fallback rule.

## Prompt

What if the memory system is installed at user level under ~/.claude/plugins/

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
