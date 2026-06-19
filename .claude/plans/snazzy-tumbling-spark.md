# Fix Doctor Test Recursion Bug

## Context

Session 32 fixed the doctor test check to target the memory-schema package's own tests instead of the consumer project's. But this introduced a recursion bug: `check_tests()` runs `pytest tests/` on the package, which collects `tests/test_cli_doctor.py`, which invokes `doctor` via `CliRunner`, which runs `check_tests()` again → infinite subprocess recursion. Each level has a 120s timeout, so it appears as a timeout.

## Prior Residuals (from [S4] c6362fe)

- None — ledger is empty

---

## Phase 1 — Exclude test_cli_doctor.py from doctor's subprocess pytest

**File:** `src/memoryschema/cli/doctor_cmd.py` (~line 315)

Add `--ignore=` for `test_cli_doctor.py` to the pytest subprocess args to break the recursion:

```python
result = subprocess.run(
    [sys.executable, "-m", "pytest", str(pkg_tests), "-q", "--tb=line",
     "--ignore=" + str(pkg_tests / "test_cli_doctor.py")],
    capture_output=True, text=True, timeout=120,
    cwd=str(pkg_root))
```

### Verify

```bash
# Should complete in <30s, not hang
timeout 30 python -m pytest tests/test_cli_doctor.py -v
pytest tests/ -x -q
```

---

## Phase 2 — Documentation alignment audit

Full audit of all docs against the fix + all prior session changes.

### 2.1 `CHANGELOG.md`

- Fixed entry for doctor test recursion bug

### 2.2 `docs/technical-reference.md`

- Doctor checks table: verify test check description notes the --ignore exclusion
- Test count: verify still accurate (707)

### 2.3 `README.md`

- Doctor section: verify check count (22) and description are current

### 2.4 `.claude-plugin/README.md`

- Verify no stale doctor references

### 2.5 Source code sweep

- Grep for any remaining references to the old `cwd=config.project_root` test pattern
- Verify the recursion fix is present

### Verify

```bash
pytest tests/ -x -q
grep -n "config.project_root" src/memoryschema/cli/doctor_cmd.py  # Should not appear in test check
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/cli/doctor_cmd.py` | Add --ignore for test_cli_doctor.py | 1 |
| `CHANGELOG.md` | Fixed entry for recursion bug | 2.1 |
| `docs/technical-reference.md` | Verify doctor check table + test count | 2.2 |
| `README.md` | Verify doctor section | 2.3 |
| `.claude-plugin/README.md` | Verify no stale refs | 2.4 |
