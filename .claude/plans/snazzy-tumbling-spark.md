# Hook Consolidation: Fix Bug, Document Formats, Extract Shared Utilities

## Context

Three issues with the hook management code:

1. **Bug**: Stop hook used `hookSpecificOutput.additionalContext` instead of `systemMessage` — fix is on disk but uncommitted, and no documentation exists about valid output formats per event type.
2. **Duplication**: Hook registration/removal/detection logic is duplicated across `hook_cmd.py`, `plugin_cmd.py`, and `doctor_cmd.py` (~200 lines of duplication). The matcher string `"Write|Edit"` appears 15+ times as a magic literal.
3. **Global gaps**: `hook_cmd.py` uninstall/status are global-only despite install supporting `--per-project`. Settings backup only happens in `plugin_cmd.py`, not `hook_cmd.py`. Timeout inconsistency (hooks.json: 15s, CLI: 10s).

## Prior Residuals (from [S4] 1efd5cb)

- None — ledger is empty

---

## Phase 1 — Bug fix + document hook output formats ✓ b174727

Single commit covering the Stop hook fix and output format documentation.

### 1.1 `src/memoryschema/hooks/hook-stop.sh`

Expand header with output format spec. The `systemMessage` fix is already on disk.

### 1.2 `src/memoryschema/hooks/hook-post-write.sh`

Add output format comment block after existing header.

### 1.3 `docs/technical-reference.md`

Insert `## Hook Output Formats` section between Pipeline and Audit Trail:
- Common fields table (all events): `continue`, `suppressOutput`, `systemMessage`, etc.
- Event-specific `hookSpecificOutput` table: supported by PreToolUse/PostToolUse/UserPromptSubmit, NOT by Stop/SessionStart/PreCompact
- Common mistake callout + correct/incorrect examples

Update CLI table: "Manage PostToolUse hook" → "Manage PostToolUse and Stop hooks"

### 1.4 `CHANGELOG.md`

Insert `### Fixed (Chain Enforcement)` entry for the `systemMessage` fix.

### Verify

```bash
pytest tests/ -x -q
grep "systemMessage" src/memoryschema/hooks/hook-stop.sh
grep "Hook Output Formats" docs/technical-reference.md
```

---

## Phase 2 — Extract shared hook utilities ✓ 6a76e9a

**New file:** `src/memoryschema/cli/_hooks_util.py`

Extract from `hook_cmd.py` and `plugin_cmd.py` into a single module:

```python
HOOK_MATCHER = "Write|Edit"
LEGACY_MATCHERS = ("Write", "Write|Edit")

def find_hook_script_path() -> str | None
def find_stop_hook_script_path() -> str | None
def get_settings_path(per_project=False, project_root=None) -> Path
def read_settings(path: Path = None) -> dict
def write_settings(path: Path, data: dict, backup: bool = True) -> None
def hook_already_registered(settings: dict, fragment="memoryschema") -> tuple[bool, str | None]
def register_hooks(settings: dict, hook_cmd: str, stop_cmd: str | None = None) -> dict
def unregister_hooks(settings: dict, fragment="memoryschema") -> tuple[dict, list[str]]
```

Key decisions:
- `backup=True` by default (plugin_cmd had it, hook_cmd didn't — consolidate on safer default)
- `HOOK_MATCHER` constant replaces all magic `"Write|Edit"` literals
- `LEGACY_MATCHERS` tuple replaces `in ("Write", "Write|Edit")` pattern
- `get_settings_path()` from hook_cmd.py becomes the shared path resolver

### Verify

```bash
pytest tests/ -x -q   # Existing tests still pass (no consumers changed yet)
python3 -c "from memoryschema.cli._hooks_util import HOOK_MATCHER; print(HOOK_MATCHER)"
```

---

## Phase 3 — Refactor hook_cmd.py to use shared utilities ✓ 7be53b7

Replace inline logic with imports from `_hooks_util`:

- Remove `_settings_path()`, `_hook_script_path()`, `_stop_hook_script_path()` — import from `_hooks_util`
- `install()`: use `register_hooks()` + `write_settings(backup=True)`
- `uninstall()`: use `unregister_hooks()` + `write_settings(backup=True)` — add backup (was missing)
- `hook_status()`: use `hook_already_registered()` from shared util
- Replace all `"Write|Edit"` / `in ("Write", "Write|Edit")` with `HOOK_MATCHER` / `LEGACY_MATCHERS`

### Verify

```bash
pytest tests/test_cli_hook.py -v    # All hook tests pass
pytest tests/ -x -q                 # Full regression
```

---

## Phase 4 — Refactor plugin_cmd.py to use shared utilities ✓ 4830f1d

Replace inline logic with imports from `_hooks_util`:

- Remove `_find_hook_script()`, `_find_stop_hook_script()`, `_read_settings()`, `_write_settings()`, `_hook_already_registered()`, `_add_hook()`, `_remove_hook()` — import from `_hooks_util`
- `deploy()`: use `register_hooks()` + `write_settings(backup=True)` + `hook_already_registered()`
- `uninstall()`: use `unregister_hooks()` + `write_settings()`
- `plugin_status()`: use `hook_already_registered()` from shared util
- Replace all matcher literals with constants

### Verify

```bash
pytest tests/test_cli_plugin.py -v   # All plugin tests pass
pytest tests/ -x -q                  # Full regression
```

---

## Phase 5 — Refactor doctor_cmd.py + consolidate tests ✓ 274a57c

### 5.1 doctor_cmd.py

Replace inline matcher check with `LEGACY_MATCHERS` import.

### 5.2 main.py

Replace matcher literal in init example output with `HOOK_MATCHER`.

### 5.3 Test consolidation

- **New file:** `tests/test_hooks_util.py` — tests for the shared utility functions (extracted from `test_cli_plugin.py` Phase 1 tests: `TestHookAlreadyRegistered`, `TestAddHook`, `TestRemoveHook`, `TestReadWriteSettings`)
- **Update `test_cli_plugin.py`** — remove helper function tests (now in `test_hooks_util.py`), keep deploy/uninstall/status command tests
- **Update `test_cli_hook.py`** — update imports, ensure tests use shared util behavior

### Verify

```bash
pytest tests/test_hooks_util.py -v    # Shared util tests pass
pytest tests/ -x -q                   # Full regression — same count, reorganized
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/hooks/hook-stop.sh` | Expand header + fix | 1.1 |
| `src/memoryschema/hooks/hook-post-write.sh` | Add output format comment | 1.2 |
| `docs/technical-reference.md` | Hook Output Formats section | 1.3 |
| `CHANGELOG.md` | Fixed entry + consolidation entry | 1.4, 5 |
| `src/memoryschema/cli/_hooks_util.py` | **New** — shared hook utilities | 2 |
| `src/memoryschema/cli/hook_cmd.py` | Refactor to use `_hooks_util` | 3 |
| `src/memoryschema/cli/plugin_cmd.py` | Refactor to use `_hooks_util` | 4 |
| `src/memoryschema/cli/doctor_cmd.py` | Use `LEGACY_MATCHERS` | 5.1 |
| `src/memoryschema/cli/main.py` | Use `HOOK_MATCHER` | 5.2 |
| `tests/test_hooks_util.py` | **New** — shared util tests | 5.3 |
| `tests/test_cli_plugin.py` | Remove helper tests (moved) | 5.3 |
| `tests/test_cli_hook.py` | Update imports | 5.3 |

## Verification (end-to-end)

```bash
pytest tests/ -x -q                           # Full suite green
memoryschema hook status                       # Both hooks reported
memoryschema doctor                            # All checks pass
python3 -c "from memoryschema.cli._hooks_util import HOOK_MATCHER; print(HOOK_MATCHER)"
grep -rn "Write|Edit" src/memoryschema/cli/    # Only in _hooks_util.py constant
```

## Status: COMPLETE

All 5 phases delivered, 5/5 PASS. 677 tests passing (+2 new).
Net code reduction: ~219 lines removed (duplication eliminated).
Session report: `docs/reports/2026-06-19-session-report-28.md`
