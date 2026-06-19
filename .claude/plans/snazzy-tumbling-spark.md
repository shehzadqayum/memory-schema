# Documentation Alignment: Sessions 26-28 Audit

## Context

A full audit of all documentation against sessions 26 (chain enforcement), 27 (plugin_cmd tests), and 28 (hook consolidation) found 4 files with gaps. The core schema, rules, and CHANGELOG are accurate — the gaps are in higher-level docs (README, technical-reference, implementation-guide, plugin README) where test counts are stale and new features (Stop hook, _hooks_util.py) are not mentioned.

**Files already accurate (no changes needed):**
- `docs/schema.md` — Edit-not-Write, Write|Edit enforcement correct
- `CHANGELOG.md` — all entries present
- `.claude-plugin/rules/memory-working.md` — Edit-not-Write present
- `.claude-plugin/rules/memory-schema.md` — Write|Edit enforcement correct
- `docs/system-overview.md` — acceptable for overview scope

## Prior Residuals (from [S4] add5988)

- None — ledger is empty

---

## Phase 1 — Fix README.md ✓ 318864c

**File:** `README.md`

- Line ~99: "PostToolUse Write hook" → "PostToolUse and Stop hooks"
- Line ~191: Hook commands description → note they manage both PostToolUse and Stop hooks
- Line ~347: Test count `569` → `677`

## Phase 2 — Fix docs/technical-reference.md ✓ 318864c

**File:** `docs/technical-reference.md`

- Line ~282: Hook CLI table → "Manage PostToolUse and Stop hooks" (already done in session 28 — verify)
- After line ~246 (Scripts section): Add `_hooks_util` module entry
- Line ~320: Test count `627` → `677`

## Phase 3 — Fix docs/implementation-guide.md ✓ 318864c

**File:** `docs/implementation-guide.md`

- Line ~70: Hook installation step → mention Stop hook is also registered
- Line ~147: Test count `627` → `677`

## Phase 4 — Fix .claude-plugin/README.md ✓ 318864c

**File:** `.claude-plugin/README.md`

- Line ~15: "Write" → "Write or Edit" in hook trigger description
- Lines ~37-47: Add Stop hook to architecture description
- After hook section: Note Stop hook fires for chain update reminders

### Verify

```bash
pytest tests/ -x -q                    # Tests still pass (docs only)
grep -rn "569\|627" docs/ README.md    # No stale test counts
grep -n "Stop" README.md .claude-plugin/README.md docs/technical-reference.md docs/implementation-guide.md  # Stop hook mentioned
```

---

## File Inventory

| File | Issues | Severity |
|------|--------|----------|
| `README.md` | Test count 569→677, hook description | HIGH |
| `docs/technical-reference.md` | Test count 627→677, _hooks_util module | MEDIUM |
| `docs/implementation-guide.md` | Test count 627→677, Stop hook setup | MEDIUM |
| `.claude-plugin/README.md` | Stop hook, Write→Write|Edit | MEDIUM |

## Status: COMPLETE

All 4 phases delivered in single commit, 4/4 PASS. 677 tests passing.
Session report: `docs/reports/2026-06-19-session-report-29.md`
