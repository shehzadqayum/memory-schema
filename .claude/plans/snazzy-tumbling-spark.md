# Resolve Residuals: plugin_cmd.py Test Coverage

## Context

`plugin_cmd.py` has had no test coverage since it was created in session 24. It has been carried as a residual through sessions 24→25→26. The module has 3 CLI commands (deploy, uninstall, status), 10 helper functions, and complex filesystem/settings interactions. This is the only actionable code residual — the other "work remaining" items (voyage API key setup, M2/M3 field spaces) are operational or gated.

## Prior Residuals (from [S4] d68182a)

- R1: `plugin_cmd.py` has no test coverage (source: session 24) → addressing in Phases 1-4

## Other Work Remaining (not in scope)

- Set `voyage.api_key` in `memoryschema.toml` — operational setup, not code work
- M2: summary/prompt spaces — gated on beating single-space baseline
- M3: mutable/drift spaces — deferred

---

## Phase 1 — Helper function unit tests

**New file:** `tests/test_cli_plugin.py`

Test the pure-logic helpers that don't need full CLI invocation:

### 1.1 `_hook_already_registered(settings, fragment)`

- Empty settings → `(False, None)`
- Settings with `"Write"` matcher containing `"memoryschema"` → `(True, cmd)`
- Settings with `"Write|Edit"` matcher containing `"memoryschema"` → `(True, cmd)`
- Settings with unrelated hooks only → `(False, None)`

### 1.2 `_add_hook(settings, hook_cmd, stop_hook_cmd)`

- Empty settings → creates PostToolUse `Write|Edit` entry
- With `stop_hook_cmd` → also creates Stop entry
- Without `stop_hook_cmd` → no Stop entry

### 1.3 `_remove_hook(settings, fragment)`

- Settings with memory-schema PostToolUse + Stop hooks → both removed, returned in list
- Settings with mixed hooks (aurora + memoryschema) → only memoryschema removed
- Settings with no matching hooks → empty removed list, settings unchanged

### 1.4 `_read_settings()` / `_write_settings(data)`

- Missing file → returns `{}`
- Valid JSON → returns parsed dict
- Write creates backup `.memory-schema-backup` before overwriting
- Write produces valid JSON with trailing newline

### 1.5 `_read_manifest()` / `_write_manifest(manifest)`

- Missing file → returns `None`
- Valid manifest → returns parsed dict
- Write produces valid JSON

### Fixtures needed

```python
@pytest.fixture
def claude_dir(tmp_path, monkeypatch):
    """Redirect CLAUDE_DIR and MANIFEST_PATH to tmp_path."""
    d = tmp_path / ".claude"
    d.mkdir()
    monkeypatch.setattr("memoryschema.cli.plugin_cmd.CLAUDE_DIR", d)
    monkeypatch.setattr("memoryschema.cli.plugin_cmd.MANIFEST_PATH", d / "memory-schema-manifest.json")
    return d

@pytest.fixture
def plugin_dir(tmp_path):
    """Create minimal .claude-plugin/ directory with all expected files."""
    ...create SKILL_FILES + RULE_FILES structure...
    return plugin
```

**Key files:**
- `tests/test_cli_plugin.py` (new)
- `src/memoryschema/cli/plugin_cmd.py` (read-only reference)

### Verify Phase 1

```bash
pytest tests/test_cli_plugin.py -v -k "not deploy and not uninstall and not status"
```

---

## Phase 2 — Deploy command tests

### 2.1 Basic deploy

- Plugin dir found, no prior deployment → creates skills, rules, memory dir, manifest, registers hook
- Verify manifest structure: `version`, `deployed_at`, `files_created`, `hook_registered`
- Verify settings.json updated with PostToolUse `Write|Edit` + Stop hooks

### 2.2 Deploy with `--force`

- Files already exist → overwrites them, manifest records `files_overwritten`

### 2.3 Deploy without `--force`

- Files already exist → skips them, output says "Exists (skip)"

### 2.4 Deploy idempotent hook

- Hook already registered → "already registered" message, `hook_was_existing=True`

### 2.5 Plugin dir not found

- `_find_plugin_dir()` returns `None` → error exit

### 2.6 Hook scripts missing

- `_find_hook_script()` returns `None` → warning but deploy continues

### Verify Phase 2

```bash
pytest tests/test_cli_plugin.py -v -k "deploy"
```

---

## Phase 3 — Uninstall command tests

### 3.1 Dry-run (no `--confirm`)

- Shows what would be removed, doesn't delete anything

### 3.2 Full uninstall (`--confirm`)

- Removes files listed in manifest, removes empty dirs, removes hook from settings, removes manifest

### 3.3 `--keep-data`

- Preserves `memory/` directory contents

### 3.4 No manifest

- "Nothing to uninstall" message

### 3.5 Hook preservation

- `hook_was_existing=True` in manifest → hook NOT removed from settings on uninstall

### Verify Phase 3

```bash
pytest tests/test_cli_plugin.py -v -k "uninstall"
```

---

## Phase 4 — Status command tests

### 4.1 Not deployed

- No manifest → "Not deployed"

### 4.2 Deployed, all healthy

- Manifest exists, all files present, hook registered → clean status output

### 4.3 Missing files

- Some deployed files deleted → reports missing count

### 4.4 Hook not registered

- Hook absent from settings.json → reports "NOT registered"

### Verify Phase 4

```bash
pytest tests/test_cli_plugin.py -v -k "status"
```

---

## Verification (end-to-end)

```bash
pytest tests/test_cli_plugin.py -v          # All plugin tests
pytest tests/ -x -q                          # Full suite regression
```

## File Inventory

| File | Change |
|------|--------|
| `tests/test_cli_plugin.py` | **New** — full test coverage for plugin_cmd.py |
