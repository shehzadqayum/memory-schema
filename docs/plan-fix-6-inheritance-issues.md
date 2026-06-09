# Fix 6 Inheritance Issues

## Context

Code review identified 6 issues in the inheritance and hierarchy implementation. All are bugs or design gaps — not feature requests.

## Fixes

### Fix 1: Fragile gap heuristic → marker-based walk
**File:** `src/memoryschema/inheritance.py`

Replace magic-number gap tolerance with marker-based walk: walk to filesystem root, only collect directories that contain the marker (`memoryschema.toml` or `.claude/rules/`). No gap counting.

Extract shared helper:
```python
def _walk_upward(start, predicate, max_depth=20):
    """Walk upward from start, collecting dirs where predicate(dir) is truthy.
    Returns results in child-first order. Stops at filesystem root or max_depth.
    """
```

This also fixes **Fix 2** (duplicate walk logic).

### Fix 2: Duplicate walk logic → shared `_walk_upward` helper
**File:** `src/memoryschema/inheritance.py`

Replace both `walk_config_chain()` and `rules_ancestry()` with calls to `_walk_upward()`:
- `walk_config_chain(root)` → `_walk_upward(root, lambda d: find_toml_config(d))`
- `rules_ancestry(root)` → `_walk_upward(root, lambda d: d/'.claude'/'rules' if (d/'.claude'/'rules').is_dir() else None)`

### Fix 3: Silent rule override → proactive warnings
**Files:** `src/memoryschema/inheritance.py`, `src/memoryschema/cli/rules_cmd.py`

Add `overridden_rules(project_root)` function that returns child rules shadowed by parent. Surface in:
- `memoryschema rules` — show `[OVERRIDDEN]` marker on child rules replaced by parent
- `resolve_rules()` — add `overridden` list to return value alongside effective rules

### Fix 4: Unbounded read-up → `max_depth` parameter
**File:** `src/memoryschema/hierarchy.py`

Add optional `max_depth` parameter to `project_matches_scope()`:
```python
def project_matches_scope(entry_project, scope_project, max_depth=None):
```
When set, limits how many hierarchy levels up or down a match can reach. `None` = unlimited (backward compatible).

### Fix 5: No TOML name validation → `validate_toml_name()` check
**File:** `src/memoryschema/inheritance.py`

Add `validate_toml_name(project_root)` that checks if `project.name` in TOML matches the expected dot-notation derived from directory structure. Returns warning string or None.

Call from `resolve_config_chain()` as a warning (not an error — advisory).

### Fix 6: Missing doctor updates → add TOML + rules inheritance checks
**File:** `src/memoryschema/cli/doctor_cmd.py`

Add two new checks after existing check 7 (guidelines):
- **Check: toml_config** — verify `memoryschema.toml` exists and parses correctly
- **Check: rules_inheritance** — report any overridden rules (parent shadowing child)

## Files to Modify

| File | Changes |
|------|---------|
| `src/memoryschema/inheritance.py` | `_walk_upward` helper, replace both walkers, `overridden_rules()`, `validate_toml_name()` |
| `src/memoryschema/hierarchy.py` | `max_depth` param on `project_matches_scope()` |
| `src/memoryschema/cli/doctor_cmd.py` | Add toml_config + rules_inheritance checks |
| `src/memoryschema/cli/rules_cmd.py` | Show overridden rules in output |
| `tests/test_inheritance.py` | Update walk tests, add override/validation tests |
| `tests/test_hierarchy.py` | Add max_depth tests for project_matches_scope |

## Verification

1. `python -m pytest tests/ -v` — all 366+ tests pass
2. `memoryschema doctor` — 20/20 checks (2 new)
3. `memoryschema rules` on a nested project — shows `[OVERRIDDEN]` markers
4. Deep directory structures (>2 intermediate dirs) correctly find parent TOML
