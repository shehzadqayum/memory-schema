# Fix 3 issues: env var precedence, redundant import, integration tests ✓ 5f7b1ef

## Context

Code review identified 3 issues: (1) env var vs TOML precedence is inverted — TOML wins over env vars because `from_toml()` passes resolved values as explicit kwargs, bypassing `default_factory`. The docstring claims env vars are highest priority but they're actually below TOML. (2) Redundant inline import at `store.py:283`. (3) No integration tests for hierarchy scoping in the store.

## Prior Residuals (from [S4] ccac373)

None.

## Fix 1: Env var precedence inversion (BUG)

**Problem:** `from_toml()` passes TOML values as explicit kwargs to `MemoryConfig(**resolved)`. Dataclass `default_factory` (which reads env vars) only runs when a field has no explicit value. So TOML beats env vars — opposite of intended design.

**Fix:** In `from_toml()`, after constructing the instance, overlay env vars on top for the fields that have env var mappings. This restores the intended precedence: env vars > CLI > parent TOML > child TOML > defaults.

**File:** `src/memoryschema/config.py` lines 109-129

```python
@classmethod
def from_toml(cls, project_root, cli_overrides=None):
    """Create config with TOML file + inheritance chain.

    Resolution order (highest to lowest):
    1. Environment variables
    2. cli_overrides dict
    3. Parent memoryschema.toml (wins over child on conflict)
    4. Child memoryschema.toml
    5. Dataclass defaults
    """
    from memoryschema.inheritance import resolve_config_chain, validate_toml_name
    resolved = resolve_config_chain(Path(project_root).resolve(), cli_overrides)
    if 'store_path' in resolved and isinstance(resolved['store_path'], str):
        resolved['store_path'] = Path(project_root) / resolved['store_path']
    instance = cls(**{k: v for k, v in resolved.items()
                     if k in cls.__dataclass_fields__})
    # Env vars override TOML — apply on top of constructed instance
    _ENV_OVERRIDES = {
        'NEO4J_URI': 'neo4j_uri',
        'NEO4J_USER': 'neo4j_user',
        'NEO4J_PASSWORD': 'neo4j_password',
        'VOYAGE_API_KEY': 'voyage_api_key',
        'MEMORY_PROJECT': 'project_name',
    }
    for env_var, field_name in _ENV_OVERRIDES.items():
        val = os.environ.get(env_var)
        if val is not None:
            setattr(instance, field_name, val)
    instance._name_warning = validate_toml_name(Path(project_root).resolve())
    return instance
```

## Fix 2: Redundant inline import (cleanup)

**File:** `src/memoryschema/store.py` line 283

Remove `from memoryschema.hierarchy import project_matches_filter` — already imported at module level on line 20.

## Fix 3: Integration tests for hierarchy scoping

**File:** `tests/test_store.py`

Add `TestHierarchyScoping` class with tests:
- `test_search_project_returns_children` — parent project sees child entities
- `test_search_project_excludes_unrelated` — unrelated project filtered out
- `test_recall_project_scope_bidirectional` — child sees parent memories
- `test_unscoped_entity_visible_everywhere` — entity with no project field visible in all scoped queries

## Files to Modify

| File | Change |
|------|--------|
| `src/memoryschema/config.py` | Fix `from_toml()` env var overlay + docstring |
| `src/memoryschema/store.py` | Remove redundant import at line 283 |
| `tests/test_store.py` | Add `TestHierarchyScoping` integration tests |
| `tests/test_inheritance.py` | Add test verifying env vars beat TOML in `from_toml()` |

## Verification

1. `python -m pytest tests/ -v` — 390 passing ✓
2. New test: env var set + TOML set for same field → env var wins via `from_toml()` ✓
3. New tests: scoped search/recall against mixed-project store ✓

## Status: COMPLETE

Session report: `docs/reports/2026-06-09-session-report-3.md`
