---
schema: 5
importance: 10
status: archived
---

Plan to align ALL documentation with implementation — 8 items, 12 files

## Observations

- 6 doc files stale: schema.md, system-overview.md, technical-reference.md, implementation-guide.md, README.md, memory-schema.md rules
- CHANGELOG is the only current doc
- hierarchy.py (9 functions) and inheritance.py (10 functions) have zero documentation
- PARENT_OF, CHILD_OF relation types undocumented in schema and rules
- memoryschema rules and config CLI commands not in any reference
- CLI self-docs stale: main.py docstring missing rules/config, init missing TOML, doctor missing new checks
- Template memory-schema.rules.tpl missing PARENT_OF/CHILD_OF
- 3 completed plan files need historical status markers

## Reasoning

Three sessions of feature work without doc updates. Expanded scope to include CLI help text, templates, and completed plan files — not just user-facing docs.

## Prompt

ensure all documentation and CLI self-docs aligned with implementation

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-3-close.
