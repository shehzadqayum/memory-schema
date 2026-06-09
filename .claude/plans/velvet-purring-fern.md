# Inheritance Code Review Fixes

## Context

Two rounds of code review identified 11 issues total (6 original + 5 follow-up) in the inheritance and hierarchy implementation. Fixes 1-6 are implemented (uncommitted on fix/inheritance-issues branch). Fixes 7-11 are planned.

## Prior Residuals

None.

## Phase 1: Fixes 1-6 (IMPLEMENTED, uncommitted)

Status: Code complete, 384 tests passing, 20/20 doctor checks. Awaiting commit.

### Fix 1: Fragile gap heuristic → marker-based `_walk_upward(start, predicate, max_depth=20)`
### Fix 2: Duplicate walk logic → shared `_walk_upward` helper (also fixes Fix 1)
### Fix 3: Silent rule override → `overridden_rules()` + `[OVERRIDDEN]` markers in CLI
### Fix 4: Unbounded read-up → `max_depth` param on `project_matches_scope()`
### Fix 5: No TOML name validation → `validate_toml_name()` advisory check
### Fix 6: Missing doctor checks → `toml_config` + `rules_inherit` (20/20 now)

## Phase 2: Fixes 7-11 (PLANNED)

### Fix 7: Dual env var reads
**Files:** `src/memoryschema/inheritance.py`, `src/memoryschema/config.py`

Remove env var reading from `inheritance.py`. Let `config.py` dataclass defaults handle env vars as before. `resolve_config_chain()` returns TOML+CLI values only — `MemoryConfig.__post_init__` already applies env var defaults via `field(default_factory)`. Fix docstring in config.py.

### Fix 8: `_name_warning` side-channel in config dict
**File:** `src/memoryschema/inheritance.py`

Remove `_name_warning` from `resolve_config_chain()` return dict. Move the check to `MemoryConfig.from_toml()` which can log/store it on the instance without polluting the kwargs dict.

### Fix 9: Unscoped entities go silent
**File:** `src/memoryschema/hierarchy.py`

Modify `project_matches_scope()` and `project_matches_filter()`: treat `None`/empty `entry_project` as matching any scope (universal visibility). Pre-hierarchy entities remain visible.

### Fix 10: Repeated lazy imports in store.py
**File:** `src/memoryschema/store.py`

Move `from memoryschema.hierarchy import project_matches_filter, project_matches_scope` to module-level. No circular dependency exists (hierarchy.py has zero internal imports).

### Fix 11: Double filesystem walk for diagnostics
**File:** `src/memoryschema/inheritance.py`

Refactor `resolve_rules()` to also return overridden info. `overridden_rules()` becomes a thin wrapper that extracts the override data. Single walk serves both.

## Files to Modify

| File | Phase 1 | Phase 2 |
|------|---------|---------|
| `src/memoryschema/inheritance.py` | Fixes 1,2,3,5 | Fixes 7,8,11 |
| `src/memoryschema/hierarchy.py` | Fix 4 | Fix 9 |
| `src/memoryschema/store.py` | — | Fix 10 |
| `src/memoryschema/config.py` | — | Fixes 7,8 |
| `src/memoryschema/cli/doctor_cmd.py` | Fix 6 | — |
| `src/memoryschema/cli/rules_cmd.py` | Fix 3 | — |
| `tests/test_inheritance.py` | +18 tests | +5 tests |
| `tests/test_hierarchy.py` | +5 tests | +3 tests |
| `tests/test_store.py` | — | +2 tests |

## Verification

1. `python -m pytest tests/ -v` — all tests pass (384 after Phase 1, ~394 after Phase 2)
2. `memoryschema doctor` — 20/20 checks
3. Pre-hierarchy entities (no project field) visible in scoped recall after Fix 9
4. No `os.environ` reads outside `config.py` after Fix 7
