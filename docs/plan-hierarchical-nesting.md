# Hierarchical Agent Nesting with Inheritance — Status: COMPLETE

## Context

Each project folder is conceptualized as an agent. Currently, memory-schema has a flat `project` field (exact-match filtering, no hierarchy). We need true hierarchical nesting: parent agents see children, children inherit from parents, traversal respects boundaries. Dot-notation (`parent.child.grandchild`) encodes hierarchy.

## Approach

Add a `hierarchy.py` utility module, extend both stores with scoped traversal, add 2 new relation types, and update CLI commands. Schema stays at v2 (dot-notation is a convention, not a structural change). Fully backward compatible.

## Implementation Phases

### Phase 1: Foundation — `hierarchy.py` (new file)
**Create** `src/memoryschema/hierarchy.py` — pure Python, zero internal deps.

Functions:
- `parse_project_path(project)` → `['a','b','c']`
- `project_depth(project)` → int
- `parent_project(project)` → `str | None`
- `ancestor_projects(project)` → `list[str]`
- `is_ancestor_of(candidate, project)` → bool
- `is_descendant_of(candidate, project)` → bool
- `project_matches_scope(entry_project, scope)` → bool (bidirectional: read-up + read-down, for recall)
- `project_matches_filter(entry_project, filter)` → bool (subtree-only: read-down, for search/list)
- `validate_project_name(project)` → `list[str]` errors

**Create** `tests/test_hierarchy.py` — full coverage.

### Phase 2: Relation Types
**Modify** these files to add `PARENT_OF`, `CHILD_OF`:
- `src/memoryschema/validator.py` — `VALID_RELATION_TYPES` frozenset (line 19)
- `src/memoryschema/neo4j_store.py` — `_RELATION_TYPES` (line 26)
- `src/memoryschema/migration.py` — `_RELATION_TYPES` (line 18)
- `src/memoryschema/config.py` — `valid_relation_types` tuple + add `project_segments`, `parent_project_name` properties
- Update tests: `test_validator.py`, `test_config.py`

### Phase 3: JSONL Store Scoping
**Modify** `src/memoryschema/store.py`:
- `search()` (line 193): exact match → `project_matches_filter()`
- `recall()` (line 437): add `project=None` param, filter `entry_map` via `project_matches_scope()`
- `list_all()` (line 222): add `project=None` param with `project_matches_filter()`
- `compute_backlinks()` (line 226): add `project=None` param
- `compute_associations()` (line 253): add `project=None` param

**Update** `tests/test_store.py` — hierarchy search, scoped recall, inheritance tests.

### Phase 4: Neo4j Store Scoping
**Modify** `src/memoryschema/neo4j_store.py`:
- `search()`: `= $project` → `STARTS WITH` prefix match
- `recall()`: add `project=None`, pass to `_vector_search()` and `_get_neighbors()`
- `_vector_search()`: over-fetch + post-filter by scope
- `_get_neighbors()`: add `WHERE` clause filtering by scope
- `list_all()`: add `project=None` with Cypher `STARTS WITH`
- `compute_backlinks()`, `compute_associations()`: add `project=None`

**Update** `tests/test_neo4j_store.py` — mocked hierarchy tests.

### Phase 5: Tags/Discovery
**Modify** `src/memoryschema/tags.py` — `_derive_project()` (line 17): detect nested `projects/<name>/projects/<child>/` → `parent.child`

**Update** `tests/test_tags.py`.

### Phase 6: CLI
**Modify** `src/memoryschema/cli/memory_cmd.py`:
- `recall` command: add `--project` option
- `search` command: add `--project` option

**Update** `tests/test_cli_memory.py`.

### Phase 7: Package/Docs
- `src/memoryschema/__init__.py` — export hierarchy functions
- `docs/schema.md` — document PARENT_OF, CHILD_OF, dot-notation convention
- `.claude/rules/memory-schema.md` — add hierarchy rules

## Key Design Decisions

- **Two matching modes**: `project_matches_scope()` (bidirectional, for recall — child sees parent memories) vs `project_matches_filter()` (subtree-only, for search/list — parent sees children)
- **Schema stays v2** — dot-notation is a convention, not a structural change
- **Neo4j vector search**: over-fetch 3x then post-filter (vector index doesn't support pre-filtering)
- **Backward compatible** — flat project names still work; `search(project='flat')` returns exact matches as before

## Files Summary

| Action | File | Change |
|--------|------|--------|
| Create | `src/memoryschema/hierarchy.py` | New module |
| Create | `tests/test_hierarchy.py` | New tests |
| Modify | `src/memoryschema/store.py` | Scoped recall/search/list/backlinks/associations |
| Modify | `src/memoryschema/neo4j_store.py` | Scoped Cypher queries |
| Modify | `src/memoryschema/validator.py` | PARENT_OF, CHILD_OF |
| Modify | `src/memoryschema/config.py` | Relation types, hierarchy properties |
| Modify | `src/memoryschema/migration.py` | Relation types |
| Modify | `src/memoryschema/tags.py` | Nested project derivation |
| Modify | `src/memoryschema/cli/memory_cmd.py` | --project on recall/search |
| Modify | `src/memoryschema/__init__.py` | Exports |
| Modify | `docs/schema.md` | Hierarchy docs |
| Modify | `.claude/rules/memory-schema.md` | Hierarchy rules |
| Modify | 6 test files | Hierarchy coverage |

## Verification

1. `python -m pytest tests/test_hierarchy.py -v` — hierarchy utils
2. `python -m pytest tests/ -v` — full suite (should be 264 + ~40 new = ~304)
3. End-to-end: write entities with `project=parent` and `project=parent.child`, verify `recall --project parent` returns both, `search --project parent.child` returns only child
4. `memoryschema doctor` — 18/18 green
