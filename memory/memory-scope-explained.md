---
schema: 5
importance: 7
status: archived
---

Memory scope: physical isolation per project (memory/ dir), logical sub-scoping via project field dot-notation

## Observations

- Physical: each project has its own memory/ directory with MEMORY.md, store.jsonl, entity files, .active_chain
- Hook derives project root from file path — finds parent of memory/ directory
- Logical: project field enables dot-notation hierarchy (org.team.sub) with bidirectional recall and subtree-only search
- Plugin scope: mechanism is global (hooks, rules, skills), data is per-project (memory/ directory)
- No cross-project recall — project A cannot see project B's memories
- Shared memories: use parent project in dot-notation hierarchy for inheritance

## Reasoning

The scoping model has two layers: physical (file system — each project's memory/ directory is isolated) and logical (project field — dot-notation enables hierarchical sub-scoping within a project). The plugin packaging doesn't change this — it provides mechanism globally while data stays per-project. This is the right separation: you install the memory system once but each project builds its own knowledge base.

## Prompt

Would each project retain its own memories? Explain memory scope.

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
