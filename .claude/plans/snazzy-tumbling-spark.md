# Fix hook check python_interpreter Validation

## Context

After Fix 1 (portable Python path), `validate_hook_python()` in `_hooks_util.py` still looks for the Python path inside the hook script by matching `MEMORYSCHEMA_PYTHON:-` or `PYTHON=` patterns. The script no longer contains a hardcoded path — it's passed as an argument via settings.json (e.g. `bash hook.sh /path/python3`). The validator doesn't check command args, so `memoryschema hook check` reports 7/8 with `python_interpreter` failing.

## Prior Residuals (from [S4] 4dfa805)

- None — ledger is empty

---

## Phase 1 — Update validate_hook_python to check command args

### 1.1 `src/memoryschema/cli/_hooks_util.py` — `validate_hook_python()`

Add optional `hook_command` parameter. After checking the script for MEMORYSCHEMA_PYTHON/PYTHON= patterns, fall back to extracting the Python path from the command string (last arg after the script path):

```python
def validate_hook_python(hook_script_path, hook_command=None):
```

If `not python_path and hook_command`: split command, take last part, check `os.path.exists()`.

### 1.2 `src/memoryschema/cli/hook_cmd.py` — `hook_check` command (~line 262)

Pass the command string to `validate_hook_python`:

```python
_check("python_interpreter",
       lambda: validate_hook_python(hook_path, hook_command=detail.get("post_tool_use_command")))
```

Need to read settings and get `detail` before the check runs. Move the `get_hook_registration_detail` call before the checks list.

### Verify

```bash
memoryschema hook check  # 8/8 passed
pytest tests/ -x -q     # Full suite green
```

---

## Phase 2 — Documentation alignment

### 2.1 `CHANGELOG.md`

- Fixed entry for hook check python_interpreter validation

### Verify

```bash
pytest tests/ -x -q
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/cli/_hooks_util.py` | Add hook_command fallback to validate_hook_python | 1.1 |
| `src/memoryschema/cli/hook_cmd.py` | Pass command string to validate_hook_python in hook check | 1.2 |
| `CHANGELOG.md` | Fixed entry | 2.1 |
