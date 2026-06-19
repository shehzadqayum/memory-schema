# memory-schema Package Fixes (3 issues from consumer project usage)

## Context

When using the memory-schema package from a consumer project (Aurora), three issues were discovered via `memoryschema doctor` (21/22 checks passing) and during normal usage:

1. The PostToolUse hook script hardcodes an absolute user-specific Python path as its default
2. The `doctor` test check runs the consumer project's tests instead of the package's own tests
3. `neo4j deploy` fails to detect Docker despite it running correctly

All three issues are in the memory-schema package itself.

## Prior Residuals (from [S4] 466f0fa)

- None — ledger is empty

---

## Phase 1 — Hook Python path resolution

**Problem:** `hook-post-write.sh` line 22 hardcodes `/Volumes/RAID0/Users/shehzad/.pyenv/versions/3.12.3/bin/python3` — non-portable.

### 1.1 `src/memoryschema/hooks/hook-post-write.sh` (line 22)

Replace hardcoded default with argument > env > auto-detect > bare python3:

```bash
# Resolve Python: argument > env var > auto-detect > bare python3
if [ -n "${1:-}" ] && [ -x "${1:-}" ]; then
    PYTHON="$1"
elif [ -n "${MEMORYSCHEMA_PYTHON:-}" ]; then
    PYTHON="$MEMORYSCHEMA_PYTHON"
else
    PYTHON=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && \
           "$candidate" -c "import memoryschema" >/dev/null 2>&1; then
            PYTHON="$candidate"
            break
        fi
    done
    if [ -z "$PYTHON" ]; then
        echo "hook: cannot find Python with memoryschema installed" >&2
        exit 0
    fi
fi
```

### 1.2 `src/memoryschema/cli/hook_cmd.py` (~line 75)

Embed `sys.executable` in the hook command: `f"bash {hook_path} {sys.executable}"`

### 1.3 `src/memoryschema/cli/_hooks_util.py` — `register_hooks()`

Same change — hook command includes `sys.executable` so Python path survives across shells.

### 1.4 `src/memoryschema/cli/plugin_cmd.py` — deploy

Same change — deploy also registers hooks with embedded Python path.

### Verify

```bash
pytest tests/ -x -q
memoryschema hook status  # Shows updated command with Python path
```

---

## Phase 2 — Doctor test check targets package tests

**Problem:** `doctor_cmd.py` runs `pytest tests/` with `cwd=config.project_root`, which runs the consumer project's tests, not memory-schema's.

**File:** `src/memoryschema/cli/doctor_cmd.py` (lines ~304-325)

**Fix:** Find the memory-schema package root via `memoryschema.__file__` and run tests from there.

### Verify

```bash
cd /some/other/project && memoryschema doctor  # Test check reports 707 passed (package tests)
pytest tests/ -x -q
```

---

## Phase 3 — Docker detection in neo4j deploy

**Problem:** `neo4j_cmd.py` line 33 `subprocess.run(["docker", "info"], check=True)` fails despite Docker running — likely PATH issue in pyenv/poetry subprocess.

**File:** `src/memoryschema/cli/neo4j_cmd.py` (lines 31-37)

**Fix:** Use `shutil.which("docker")` with fallback to common locations (`/usr/local/bin/docker`, `/usr/bin/docker`, `/opt/homebrew/bin/docker`). Better diagnostics on failure.

### Verify

```bash
memoryschema neo4j status  # Should detect Docker correctly
pytest tests/ -x -q
```

---

## Phase 4 — Documentation alignment audit

Full audit of all docs against phases 1-3 changes. Same pattern as sessions 29-31.

### 4.1 `CHANGELOG.md`

- Fixed entries for all 3 issues (hook Python path, doctor test target, Docker detection)

### 4.2 `README.md`

- Hook install section: mention that Python path is embedded in the command
- Doctor section: note that doctor runs package tests (not consumer project tests)
- Neo4j section: mention improved Docker detection with PATH fallbacks

### 4.3 `docs/technical-reference.md`

- Hook management section: document Python path resolution chain (arg > env > auto-detect)
- Doctor checks: update test check description
- Update test count if changed

### 4.4 `docs/implementation-guide.md`

- Hook setup step: mention that `hook install` embeds the current Python path
- Update test count if changed

### 4.5 `.claude-plugin/README.md`

- Hook section: note Python path auto-detection
- Verify no hardcoded paths remain

### 4.6 Source code sweep

- Grep for any remaining hardcoded `pyenv.*3.12.3` paths in src/ and docs/
- Verify all hook registration paths use `sys.executable`

### Verify

```bash
pytest tests/ -x -q
grep -rn "pyenv.*3.12.3" src/ docs/  # No hardcoded paths remain
grep -rn "upgrade\|check\|scan" README.md docs/technical-reference.md  # Commands still documented
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/hooks/hook-post-write.sh` | Replace hardcoded Python with resolution chain | 1.1 |
| `src/memoryschema/cli/hook_cmd.py` | Embed sys.executable in hook command | 1.2 |
| `src/memoryschema/cli/_hooks_util.py` | Embed sys.executable in register_hooks | 1.3 |
| `src/memoryschema/cli/plugin_cmd.py` | Embed sys.executable in deploy | 1.4 |
| `src/memoryschema/cli/doctor_cmd.py` | Fix test check to target package tests | 2 |
| `src/memoryschema/cli/neo4j_cmd.py` | Improve Docker detection with shutil.which | 3 |
| `CHANGELOG.md` | Fixed entries for all 3 issues | 4.1 |
| `README.md` | Hook Python path, doctor target, Docker detection | 4.2 |
| `docs/technical-reference.md` | Hook resolution chain, doctor check, test count | 4.3 |
| `docs/implementation-guide.md` | Hook install Python path, test count | 4.4 |
| `.claude-plugin/README.md` | Python path auto-detection | 4.5 |
| `CHANGELOG.md` | Fixed entries for all 3 issues | 4.1 |
