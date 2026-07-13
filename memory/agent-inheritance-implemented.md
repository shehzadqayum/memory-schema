---
schema: 5
type: episodic
importance: 10
relations:
  - DEPENDS_ON deployment-verified
---

Implemented agent rules and config inheritance with parent-absolute authority

## Observations

- New inheritance.py module: TOML config, chain walking, parent-wins merge, rules resolution
- MemoryConfig.from_toml() classmethod for TOML-based construction
- CLI commands: memoryschema rules, memoryschema config
- Parent overrides child on conflict for both rules and config
- Child self-governs when parent is absent (no TOML/rules above)
- Walk skips intermediate dirs (e.g. projects/), stops after 2 consecutive misses
- 366 tests passing, 18/18 doctor checks

## Reasoning

Completes the agent model: memories (bidirectional, already done) + rules (parent wins) + config (parent wins). Three inheritance channels now operational. The parent-absolute authority model means children cannot resist parent policy.

## Prompt

implement agent inheritance plan

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: MODIFIES nested-agents-discussion.
