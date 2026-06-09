# Resolve reflect CLI residual

## Context

From [S4] `15d8e4d` residual: `reflect()` in `consolidation.py` (line 204) is callable from Python but has no CLI wrapper. This is the only outstanding residual across all sessions.

## Prior Residuals (from [S4] 15d8e4d)

- R1: reflect() CLI command — addressing (this plan)

## Fix

### 1. Add CLI command
**Create** `src/memoryschema/cli/reflect_cmd.py` — wraps `consolidation.reflect()` with options for project, min/max cluster, dry-run, json output.

### 2. Register command
**Modify** `src/memoryschema/cli/main.py` — import, register, update docstring.

### 3. Export function
**Modify** `src/memoryschema/__init__.py` — add `reflect` to imports and `__all__`.

### 4. Tests
**Create** `tests/test_cli_reflect.py` — dry-run, json output, no-episodic graceful handling.

## Files to Modify

| Action | File | Change |
|--------|------|--------|
| Create | `src/memoryschema/cli/reflect_cmd.py` | New CLI command |
| Create | `tests/test_cli_reflect.py` | Tests |
| Modify | `src/memoryschema/cli/main.py` | Import + register + docstring |
| Modify | `src/memoryschema/__init__.py` | Export reflect |

## Verification

1. `memoryschema reflect --help` — shows options
2. `memoryschema reflect --dry-run` — runs without error
3. `python -m pytest tests/test_cli_reflect.py -v` — tests pass
4. `python -m pytest tests/ -v` — full suite passes
5. `memoryschema doctor` — all checks pass
