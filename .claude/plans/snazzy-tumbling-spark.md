# Fix Neo4j Test Mocks After Docker Detection Refactor

## Context

Session 32 refactored Docker detection in `neo4j_cmd.py` from `subprocess.run(["docker", "info"], check=True)` to `_find_docker()` (using `shutil.which`) + `_check_docker()`. Two tests in `test_cli_neo4j.py` fail because they only mock `subprocess.run` but not `shutil.which`, so `_find_docker()` finds the real Docker binary and the mock chain breaks.

## Prior Residuals (from [S4] 7452911)

- None — ledger is empty

---

## Phase 1 — Update neo4j test mocks with shutil.which ✓ 289e16f

**File:** `tests/test_cli_neo4j.py`

For tests simulating Docker availability: add `patch("memoryschema.cli.neo4j_cmd.shutil.which", return_value="/usr/local/bin/docker")` and align `subprocess.run` side_effect to match the new call pattern (info_result first, then ps_result).

For tests simulating Docker unavailable: mock `shutil.which` to return `None` and `os.path.exists` to return `False`.

Specific tests to update:
- `test_status_json_docker_available` — add shutil.which mock, fix side_effect order
- `test_status_text_container_not_created` — add shutil.which mock, fix side_effect order
- `test_status_json_docker_unavailable` — mock shutil.which → None
- `test_status_text_docker_not_found` — mock shutil.which → None

### Verify

```bash
python -m pytest tests/test_cli_neo4j.py -v  # 9/9 passed
pytest tests/ -x -q  # Full suite green
```

---

## Phase 2 — Documentation alignment ✓ 289e16f

### 2.1 `CHANGELOG.md`

- Fixed entry for neo4j test mock update

### Verify

```bash
pytest tests/ -x -q
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `tests/test_cli_neo4j.py` | Add shutil.which mocks, align subprocess side_effects | 1 |
| `CHANGELOG.md` | Fixed entry | 2.1 |

## Status: COMPLETE

All 2 phases delivered, 2/2 PASS. 707 tests passing (9/9 neo4j tests green).
Session report: `docs/reports/2026-06-19-session-report-34.md`
