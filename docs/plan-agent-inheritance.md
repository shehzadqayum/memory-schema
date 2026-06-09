# Agent Inheritance: Rules & Config

## Context

Each project folder is an agent. Agents are nested (parent contains child). The inheritance model:
- **Memories**: shared via containment (bidirectional) — ALREADY IMPLEMENTED
- **Rules**: cascade downward, **parent overrides child on conflict**
- **Config**: cascade downward, parent's config is the default, parent wins on conflict

Agents communicate through shared memories. Parent's scope includes everything in the child's scope.

## Approach

New `inheritance.py` module for TOML config loading + rules resolution. Config via `memoryschema.toml` files with upward chain walking. Rules via `.claude/rules/` directory composition. Parent always wins on conflict. Fully backward compatible — existing env-var config and flat projects still work.

## Config File Format (`memoryschema.toml`)

```toml
[project]
name = "workspace"

[store]
path = "memory/store.jsonl"

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
password = "changeme"

[voyage]
embed_model = "voyage-4-lite"

[retrieval]
recency_decay = 0.995
recall_depth = 2
```

## Resolution Order (highest to lowest precedence)

1. Environment variables
2. CLI flags (`--project`, `--root`)
3. Parent `memoryschema.toml` (wins over child on conflict)
4. Child `memoryschema.toml`
5. `MemoryConfig` dataclass defaults

## Rules Resolution

Parent wins on filename conflict. Child's unique rules are additive.

Example: parent has `memory-schema.md` + `memory-working.md`, child has `memory-working.md` + `custom.md`. Effective set: parent's `memory-schema.md`, parent's `memory-working.md`, child's `custom.md`.

Walk stops when a directory has no `.claude/rules/` (not a managed agent).

## Implementation Steps

### Step 1: `src/memoryschema/inheritance.py` (new)
Core module with:
- `find_toml_config(project_root)` → `Path | None`
- `load_toml_config(path)` → dict (uses stdlib `tomllib`)
- `flatten_toml(toml_dict)` → flat dict mapping to MemoryConfig fields
- `walk_config_chain(project_root)` → `list[Path]` (child-first, stops at gap)
- `merge_config_dicts(child, parent)` → dict (parent wins on conflict)
- `resolve_config_chain(project_root, cli_overrides=None)` → dict
- `rules_ancestry(project_root)` → `list[Path]` of `.claude/rules/` dirs
- `resolve_rules(project_root)` → `list[dict]` with filename, source, is_inherited

### Step 2: `src/memoryschema/config.py` modifications
- Add `config_file_path` property
- Add `MemoryConfig.from_toml(project_root, cli_overrides=None)` classmethod
- Existing `__init__`/`__post_init__` unchanged (backward compatible)

### Step 3: `src/memoryschema/templates/memoryschema.toml.tpl` (new)
TOML template for `memoryschema init`

### Step 4: `src/memoryschema/cli/main.py` modifications
- `cli()` callback: use `from_toml()` when TOML exists
- `init` command: generate `memoryschema.toml`, detect parent for dot-name derivation

### Step 5: New CLI commands
- `src/memoryschema/cli/rules_cmd.py` — `memoryschema rules [--json] [--conflicts]`
- `src/memoryschema/cli/config_cmd.py` — `memoryschema config [--json] [--chain]`
- Register both in `main.py`

### Step 6: `src/memoryschema/cli/doctor_cmd.py` modifications
- Add TOML validity check
- Add rules inheritance conflict reporting

### Step 7: `src/memoryschema/__init__.py`
- Export `resolve_config_chain`, `resolve_rules`

### Step 8: `tests/test_inheritance.py` (new, ~41 tests)
- TOML parsing (~8 tests)
- Config chain walking (~6 tests)
- Config merging with parent-wins (~8 tests)
- Full resolution (~5 tests)
- Rules resolution with parent-wins (~10 tests)
- CLI integration (~4 tests)

## Files Summary

| Action | File | Change |
|--------|------|--------|
| Create | `src/memoryschema/inheritance.py` | Config chain + rules resolution |
| Create | `tests/test_inheritance.py` | ~41 tests |
| Create | `src/memoryschema/templates/memoryschema.toml.tpl` | Config template |
| Create | `src/memoryschema/cli/rules_cmd.py` | Rules diagnostic command |
| Create | `src/memoryschema/cli/config_cmd.py` | Config diagnostic command |
| Modify | `src/memoryschema/config.py` | `from_toml()`, `config_file_path` |
| Modify | `src/memoryschema/cli/main.py` | TOML loading in CLI, init generates TOML |
| Modify | `src/memoryschema/cli/doctor_cmd.py` | TOML + rules inheritance checks |
| Modify | `src/memoryschema/__init__.py` | New exports |

## Key Design Decisions

- **Parent wins on conflict** — enforcement hierarchy, not customization
- **Walk stops at gap** — no `memoryschema.toml` or `.claude/rules/` = not a managed agent
- **`inheritance.py` separate from `hierarchy.py`** — hierarchy is string ops, inheritance is filesystem
- **`tomllib` (stdlib 3.11+)** — no new dependencies; fallback `tomli` for 3.10
- **Backward compatible** — `MemoryConfig()` still works without TOML; `from_toml()` is additive

## Verification

1. `python -m pytest tests/test_inheritance.py -v` — inheritance tests
2. `python -m pytest tests/ -v` — full suite (325 existing + ~41 new = ~366)
3. End-to-end: create parent + child projects with conflicting rules and config, verify parent wins
4. `memoryschema doctor` — all checks pass
5. `memoryschema rules` — shows effective rules with inheritance markers
6. `memoryschema config --chain` — shows config sources
