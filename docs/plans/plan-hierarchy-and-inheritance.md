> Superseded by [docs/hierarchy-and-inheritance.md](../hierarchy-and-inheritance.md). Retained for implementation history.

# Hierarchy and Inheritance — Status: COMPLETE

## Context

Each project folder is an agent. Memory-schema originally had a flat `project` field with exact-match filtering. This plan covers three phases of work that added true hierarchical nesting and config/rules inheritance:

1. **Hierarchical nesting** — dot-notation project names, scoped traversal, two matching modes
2. **Agent inheritance** — TOML config chain, rules resolution, parent-absolute authority
3. **Code review fixes** — shared walker, overridden rules, max_depth, TOML name validation

All three phases are implemented and tested.

## Architecture

### Two Modules, Two Concerns

| Module | Domain | Dependencies |
|--------|--------|--------------|
| `hierarchy.py` | String operations on dot-notation names | None (pure Python) |
| `inheritance.py` | Filesystem walking for TOML config and rules | `tomllib`, `hierarchy.py` (lazy) |

### Two Matching Modes

| Mode | Function | Direction | Used by |
|------|----------|-----------|---------|
| **Scope** | `project_matches_scope()` | Bidirectional (child sees parent, parent sees child) | `recall()` |
| **Filter** | `project_matches_filter()` | Subtree-only (parent sees children) | `search()`, `list_all()`, `compute_backlinks()`, `compute_associations()` |

Both modes treat unscoped entities (no project field) as universally visible.

### Config Resolution Order

1. Environment variables (highest precedence)
2. CLI flags
3. Parent `memoryschema.toml` (wins over child on conflict)
4. Child `memoryschema.toml`
5. `MemoryConfig` dataclass defaults

### Rules Resolution

Parent wins on filename conflict. Child's unique rules are additive. Walk uses `_walk_upward()` shared helper with marker-based detection (no gap counting).

## Implementation Summary

### hierarchy.py
- `parse_project_path`, `project_depth`, `parent_project`, `ancestor_projects`
- `is_ancestor_of`, `is_descendant_of`
- `project_matches_scope` (with `max_depth` parameter), `project_matches_filter`
- `validate_project_name`

### inheritance.py
- `_walk_upward` — shared marker-based upward walker
- `find_toml_config`, `load_toml_config`, `flatten_toml`
- `walk_config_chain`, `merge_config_dicts`, `resolve_config_chain`
- `rules_ancestry`, `resolve_rules` (returns effective + overridden tuple)
- `overridden_rules`, `validate_toml_name`

### Store Scoping
- **JSONL store**: Uses `project_matches_filter`/`project_matches_scope` from hierarchy.py
- **Neo4j store**: Reimplements with Cypher `STARTS WITH` + `IS NULL` (can't call Python from Cypher)

### Relation Types
- Added `PARENT_OF`, `CHILD_OF` to the canonical set (8 total)
- Single source of truth in `config.py`, imported by validator, neo4j_store, migration

### CLI
- `--project` option on `recall` and `search`
- `memoryschema rules [--json] [--conflicts]`
- `memoryschema config [--json] [--chain]`
- Doctor checks: `toml_config`, `rules_inheritance`

## Design Decisions

- **Parent wins on conflict** — enforcement hierarchy, not customization
- **Schema stays v3** — dot-notation is a convention, not a structural change
- **`hierarchy.py` separate from `inheritance.py`** — hierarchy is string ops, inheritance is filesystem
- **Neo4j vector search**: over-fetch 3x then post-filter (vector index doesn't support pre-filtering)
- **Backward compatible** — flat project names and env-var-only config still work unchanged
- **Marker-based walk** — replaced fragile gap heuristic with `_walk_upward(start, predicate, max_depth=20)`

## Files

| Module | Files |
|--------|-------|
| Hierarchy | `src/memoryschema/hierarchy.py`, `tests/test_hierarchy.py` |
| Inheritance | `src/memoryschema/inheritance.py`, `tests/test_inheritance.py` |
| Config | `src/memoryschema/config.py` (constants, `from_toml()`, properties) |
| Stores | `src/memoryschema/store.py`, `src/memoryschema/neo4j_store.py` |
| Validator | `src/memoryschema/validator.py` (imports from config) |
| Migration | `src/memoryschema/migration.py` (imports from config) |
| Tags | `src/memoryschema/tags.py` (`_derive_project` with kebab validation) |
| CLI | `cli/memory_cmd.py`, `cli/rules_cmd.py`, `cli/config_cmd.py`, `cli/doctor_cmd.py` |
| Templates | `templates/memoryschema.toml.tpl` |
| Package | `__init__.py` (exports hierarchy + inheritance functions) |
