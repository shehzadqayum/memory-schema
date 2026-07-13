---
schema: 5
importance: 9
status: archived
relations:
  - MODIFIES inheritance-review-fixes
---

Full package audit plan — 15 items: 13 code fixes + doc consolidation + doc sync pass

## Observations

- CRITICAL: Cypher injection via f-string in neo4j_store.py:109-113 — rel_type interpolated into query, allowlist is only guard
- HIGH: Neo4j project scoping missing OR m.project IS NULL for unscoped entities — diverges from JSONL store behavior
- HIGH: Relation type constants duplicated in 4 files (config, validator, neo4j_store, migration)
- HIGH: tags.py defaults type to empty string instead of semantic (line 75)
- HIGH: Hook script silent failure when both Neo4j and JSONL fail — 2>/dev/null suppresses stderr
- HIGH: tomllib import without Python 3.10 fallback (requires-python says >=3.10)
- MEDIUM: Duplicated scoring logic between _score_entry and _score_all_entries numpy path
- MEDIUM: Upsert merges filepath and schema — unclear mutability semantics
- MEDIUM: _derive_project can produce invalid project names from malformed paths
- LOW: Dead imports in tags.py (os, discover_memory_files)
- DOCS: Consolidate 3 completed plan docs into docs/plan-hierarchy-and-inheritance.md
- DOCS: Final sync pass — update test counts, doctor checks, type defaults across 7 doc files

## Reasoning

Three parallel audit agents covered core data path, integration modules, and CLI/tests/package. All agent findings verified against current code — 4 claims disproven. 390 tests passing, package fundamentally sound but needs defense-in-depth improvements.

## Notes

Plan location: `.claude/plans/polymorphic-rolling-mccarthy.md`
Prior residuals: None (from [S4] b3226f3).

## Git Operations

- `1a97271` — `[S1] Full package audit — 13 findings` — Plan committed and pushed
- `1b6539f` — `[S1] Full package audit — 15 items (expanded)` — Added doc consolidation + sync pass
- `bbf9fc5` — `[S2] Harden Cypher injection defense in neo4j_store` — Item 1: explicit ValueError on invalid rel_type
- `0634851` — `[S2] Add unscoped entity visibility to Neo4j queries` — Item 2: OR m.project IS NULL in 5 queries
- `233880f` — `[S2] Single source of truth for relation types` — Item 3: config.py canonical, 3 importers
- `03dec29` — `[S2] Default type to semantic when omitted` — Item 4: tags.py type default fixed
- `9e2e313` — `[S2] Exit 2 when both stores fail, remove stderr suppression` — Items 5+10: hook reliability
- `2a9cacb` — `[S2] Bump requires-python to 3.11 for tomllib` — Item 6: Python version requirement
- `4ac85fb` — `[S2] Deduplicate scoring logic via precomputed_relevance` — Items 7+13: scoring DRY
- `7757856` — `[S2] Make schema and filepath immutable in upsert merge` — Item 8: upsert semantics
- `4d784a3` — `[S2] Validate _derive_project segments are kebab-case` — Item 9: invalid project names
- `70b8f5b` — `[S2] Remove dead imports os and discover_memory_files` — Item 11: dead imports
- `19e6faf` — `[S2] Remove F2 from validation rules` — Item 12: docs alignment
- `3038cb4` — `[S2] Consolidate 3 plan docs into plan-hierarchy-and-inheritance` — Item 14: unified doc
- `710dc70` — `[S2] Final documentation sync — counts, Python version, F2 note` — Item 15: doc sync
- `23d474b` — `[S3] Session 5 checkpoint — 15/15 audited PASS` — Feedback commit
- `98cf53f` — `[S4] session close — full package audit` — Unit of work ID

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-4-close.
