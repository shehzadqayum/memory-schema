# Hook Management System + Chain Reasoning Accumulation

## Context

Two issues:

1. **Hook management gaps**: No upgrade path for stale installations (old `"Write"` matcher), no cross-project visibility, no deep troubleshooting, no version tracking. Projects that installed hooks before the `Write|Edit` and Stop hook changes are silently broken — `hook install` sees them as "already registered" and does nothing.

2. **Chain reasoning loss**: `<memory:reasoning>` is replaced on every chain update, losing the narrative evolution. Observations append; reasoning should too for chain entities.

## Prior Residuals (from [S4] c003e35)

- None — ledger is empty

---

## Phase 1 — `_hooks_util.py`: Add 8 utility functions + version constant

**File:** `src/memoryschema/cli/_hooks_util.py` (~150 lines added)

- `HOOK_VERSION = "2"` — v0=not installed, v1=Write only, v2=Write|Edit+Stop
- `get_hook_registration_detail(settings, hook_script_path, stop_script_path) → dict` — core inspection: matchers, staleness, script existence/executability, needs_upgrade, upgrade_reasons
- `detect_hook_version(detail) → str` — returns "0"/"1"/"2"
- `upgrade_hooks(settings, hook_script_path, stop_script_path) → list[str]` — in-place upgrade: Write→Write|Edit, add Stop if missing
- `find_project_settings(scan_dirs) → list[dict]` — walk directories for .claude/settings.json
- `validate_hook_python(hook_script_path) → tuple[bool, str]` — check Python interpreter from script
- `dry_run_post_tool_use_hook(hook_script_path) → tuple[bool, str, int]` — pipe synthetic JSON, check exit
- `dry_run_stop_hook(stop_script_path) → tuple[bool, str, int]` — pipe {}, validate JSON output

### Verify

```bash
pytest tests/test_hooks_util.py -v
pytest tests/ -x -q
```

---

## Phase 2 — `tests/test_hooks_util.py`: Tests for new utilities

**File:** `tests/test_hooks_util.py` (~120 lines added)

- `TestGetHookRegistrationDetail` — stale matcher, missing Stop, all current, not installed
- `TestDetectHookVersion` — v0/v1/v2 detection
- `TestUpgradeHooks` — Write→Write|Edit, add Stop, already current (no-op)
- `TestFindProjectSettings` — finds global, finds project-level, skips missing

### Verify

```bash
pytest tests/test_hooks_util.py -v
pytest tests/ -x -q
```

---

## Phase 3 — `hook_cmd.py`: Enhance status + add upgrade/check/scan

**File:** `src/memoryschema/cli/hook_cmd.py` (~120 lines added, ~30 modified)

- **Enhance `hook status`**: Add `--json` flag, use `get_hook_registration_detail()`, show version/staleness/missing
- **New `hook upgrade`**: `--per-project`, `--dry-run` flags. Read settings, check if needs_upgrade, call upgrade_hooks(), write with backup
- **New `hook check`**: 8 diagnostic checks (script exists, executable, Python valid, dry-run PostToolUse, dry-run Stop, sentinel writable, etc.)
- **New `hook scan`**: Find all project settings, show table (scope | matcher | stop | version | status), summary

### Verify

```bash
pytest tests/test_cli_hook.py -v
pytest tests/ -x -q
```

---

## Phase 4 — `tests/test_cli_hook.py`: Tests for new commands

**File:** `tests/test_cli_hook.py` (~150 lines added)

- `TestHookUpgrade` — upgrade from v1 to v2, already current, dry-run
- `TestHookCheck` — all checks pass, script missing fails
- `TestHookScan` — finds global installation, reports version

### Verify

```bash
pytest tests/test_cli_hook.py -v
pytest tests/ -x -q
```

---

## Phase 5 — `doctor_cmd.py`: Delegate 3 hook checks

**File:** `src/memoryschema/cli/doctor_cmd.py` (~30 lines modified)

Replace inline `check_hook()`, `check_hook_script()`, `check_stop_hook()` with calls to `get_hook_registration_detail()`. Add staleness detection (currently only checks existence).

### Verify

```bash
pytest tests/ -x -q
memoryschema doctor
```

---

## Phase 6 — Chain reasoning accumulation: store.py + schema + rules

### 6.1 `src/memoryschema/store.py` (line ~274)

Move `reasoning` out of flat replace loop. For `chain-*` entities, append with `\n---\n` separator. For standalone entities, replace (current behavior).

### 6.2 `docs/schema.md`

Upsert merge table: reasoning → "Replaced (standalone) / Appended with `---` separator (chain entities)"
Chain lifecycle: "append reasoning" instead of "replace reasoning"

### 6.3 `src/memoryschema/templates/memory-working.tpl`

Update Edit pattern: step 3 → "Append to `<memory:reasoning>` — add new narrative after `---` separator"

### 6.4 `.claude-plugin/rules/memory-working.md`

Same Edit pattern update as template.

### Verify

```bash
pytest tests/test_store.py -v -k "reasoning"
pytest tests/ -x -q
```

---

## Phase 7 — Tests for chain reasoning + deploy rules

### 7.1 `tests/test_store.py`

- `test_chain_reasoning_appends` — upsert chain-* entity twice, verify `---` separator
- `test_standalone_reasoning_replaces` — upsert non-chain entity twice, verify replacement

### 7.2 Deploy updated rules

```bash
memoryschema plugin deploy --force
```

### Verify

```bash
pytest tests/ -x -q                    # Full suite
grep "Append.*reasoning" docs/schema.md  # Schema updated
grep "---.*separator" ~/.claude/rules/memory-working.md  # Deployed
```

---

## Phase 8 — Documentation alignment audit

Full audit of all docs against phases 1-7 changes. Same pattern as session 29.

### 8.1 `README.md`

- Hook commands table: add `upgrade`, `check`, `scan` commands
- Hook description: mention version tracking, upgrade path, cross-project scan
- Test count: update to reflect new tests added in phases 2, 4, 7
- Chain section: mention reasoning accumulation for chain entities

### 8.2 `docs/technical-reference.md`

- CLI commands table: add `hook upgrade`, `hook check`, `hook scan`
- Scripts/module table: update `_hooks_util` entry with new functions
- Test count: update total
- Doctor checks count: update if changed

### 8.3 `docs/implementation-guide.md`

- Hook setup section: mention `hook upgrade` for existing installations
- Test count: update

### 8.4 `.claude-plugin/README.md`

- Hook section: mention upgrade path for stale installations
- Chain section: note reasoning accumulation

### 8.5 `CHANGELOG.md`

- Added entries for hook management commands (upgrade/check/scan)
- Changed entry for chain reasoning accumulation

### Verify

```bash
grep -rn "upgrade\|check\|scan" README.md docs/technical-reference.md  # New commands documented
grep -rn "reasoning.*append\|accumul" README.md .claude-plugin/README.md  # Reasoning mentioned
pytest tests/ -x -q  # Still green
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/cli/_hooks_util.py` | +8 functions, +1 constant | 1 |
| `tests/test_hooks_util.py` | +4 test classes (~20 tests) | 2 |
| `src/memoryschema/cli/hook_cmd.py` | Enhanced status + upgrade/check/scan | 3 |
| `tests/test_cli_hook.py` | +3 test classes (~15 tests) | 4 |
| `src/memoryschema/cli/doctor_cmd.py` | Delegate 3 checks | 5 |
| `src/memoryschema/store.py` | Chain-aware reasoning append | 6.1 |
| `docs/schema.md` | Reasoning merge + chain lifecycle | 6.2 |
| `src/memoryschema/templates/memory-working.tpl` | Edit pattern update | 6.3 |
| `.claude-plugin/rules/memory-working.md` | Edit pattern update | 6.4 |
| `tests/test_store.py` | +2 reasoning tests | 7.1 |
| `README.md` | Hook commands + test count + reasoning | 8.1 |
| `docs/technical-reference.md` | CLI table + module table + test count | 8.2 |
| `docs/implementation-guide.md` | Upgrade path + test count | 8.3 |
| `.claude-plugin/README.md` | Upgrade + reasoning | 8.4 |
| `CHANGELOG.md` | New entries for all changes | 8.5 |
