# Changelog

## [Unreleased]

### Added
- `hierarchy.py` — dot-notation project hierarchy utilities (parse, ancestor, scope/filter)
- `inheritance.py` — TOML config loading, rules resolution with parent-wins authority
- `PARENT_OF`, `CHILD_OF` relation types for agent hierarchy edges
- `MemoryConfig.from_toml()` classmethod for TOML-based config with inheritance
- `memoryschema rules` CLI command — show effective rules with inheritance markers
- `memoryschema config` CLI command — show effective config with chain sources
- `memoryschema.toml` template generated on `memoryschema init`
- `max_depth` parameter on `project_matches_scope()` for bounded read-up
- `validate_toml_name()` advisory check for project name / directory mismatch
- `overridden_rules()` for detecting parent-shadowed child rules
- Doctor checks: `toml_config`, `rules_inherit` (now 20/20)
- `--project` option on `recall` and `search` CLI commands

### Changed
- `resolve_rules()` now returns `(effective, overridden)` tuple (single walk)
- Unscoped entities (None/empty project) are universally visible in scoped queries
- Store scoping uses module-level imports instead of repeated inline imports

### Fixed
- Neo4j status Docker detection — split availability from container status
- `init --with-neo4j` — duplicate config argument in `ctx.invoke`
- Doctor test check — cwd resolution, timeout (30s→120s), output parsing
- Fragile gap heuristic replaced with marker-based `_walk_upward()`
- Duplicate walk logic unified into shared helper
- Dual env var reads removed from `inheritance.py`
- `_name_warning` side-channel removed from config resolution dict
- Direct `os.environ` reads removed from `neo4j_store.py` and `embeddings.py` — centralized in `config.py`
