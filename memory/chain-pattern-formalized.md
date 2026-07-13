---
schema: 5
importance: 8
relations:
  - SUPERSEDES chain-entity-design
  - SUPERSEDES chain-not-formalized
---

Chain entity pattern formalized in schema spec, rules, and working guidelines

## Observations

- Added to docs/schema.md: full spec with structure, XML example, retrieval behavior, when-to-create guidance
- Added to .claude/rules/memory-schema.md: Rule 9 — concise chain pattern definition (loaded into every conversation)
- Added to .claude/rules/memory-working.md: chain creation guidance — prefer one chain over multiple disconnected episodics
- Pattern: chain- prefix, semantic type, ordered step observations, USES relations to evidence, trigger as prompt

## Reasoning

The chain pattern was working empirically but undocumented. Formalizing in the schema spec (source of truth), rules file (loaded every conversation), and working guidelines (behavioral instruction) ensures future sessions know the pattern exists and how to apply it. The rules file is the critical one — it's in every conversation's system prompt.

## Prompt

User asked to formalize the chain entity pattern in documentation

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
