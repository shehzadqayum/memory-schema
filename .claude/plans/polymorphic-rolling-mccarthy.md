# Full Package Audit: memory-schema

## Context

Full integrity audit of the `packages/memory-schema` package. Three parallel agents examined: (1) core data path (store, validator, tags, schema, discovery), (2) integration modules (neo4j_store, embeddings, reembed, consolidation, migration), (3) CLI, tests, and package integrity. All findings verified against the current code.

390 tests pass. The package is well-structured with solid fundamentals. The issues below are ordered by severity.

## Prior Residuals (from [S4] b3226f3)

None.

---

## Verified Findings

### CRITICAL

#### 1. Cypher injection via f-string in neo4j_store.py ✓ bbf9fc5
**File:** `src/memoryschema/neo4j_store.py:109-113`
```python
session.run(f"""
    MATCH (s:Memory {{name: $source}})
    MERGE (t:Memory {{name: $target}})
    MERGE (s)-[r:{rel_type}]->(t)
""", source=name, target=target)
```
`rel_type` is interpolated directly into the Cypher query. The guard at line 108 (`rel_type in _RELATION_TYPES`) prevents exploitation *today*, but this is defense-in-depth failure. Neo4j doesn't support parameterized relationship types, so the allowlist check is the only barrier. If `_RELATION_TYPES` ever drifts or is bypassed, this becomes exploitable.

**Fix:** Add explicit `ValueError` raise before the query (not just a silent `continue`). Add a comment explaining why f-string is necessary here and that the allowlist is the security boundary.

---

### HIGH

#### 2. Neo4j project scoping reimplements hierarchy logic ✓ 0634851
**File:** `src/memoryschema/neo4j_store.py:170-174, 189-191, 402-407, 431-434`

The Neo4j store reimplements hierarchy matching with raw string operations:
```python
WHERE m.project = $project OR m.project STARTS WITH $project_prefix
```
The JSONL store uses `project_matches_filter()` / `project_matches_scope()` from `hierarchy.py`.

**Two behavioral divergences:**
- **Neo4j `list_all` (line 172):** Missing unscoped entity handling. Entities with no `project` field are excluded. The JSONL store includes them (via `project_matches_filter(None, 'a') → True`). Need `OR m.project IS NULL` in the WHERE clause.
- **Neo4j `_vector_search` (line 405):** Includes `OR $project STARTS WITH (node.project + '.')` for bidirectional scope (correct for recall), but `list_all` and `search` don't — and they shouldn't. However, `list_all` is subtree-only but `search` (line 189-191) is also subtree-only, which is correct. The issue is only the missing NULL handling.
- **`max_depth` parameter:** `project_matches_scope` now supports `max_depth` limiting. Neo4j queries don't honor this.

**Fix:** Add `OR m.project IS NULL` to `list_all`, `search`, and `_vector_search` WHERE clauses to match JSONL store behavior for unscoped entities.

#### 3. Relation type constants duplicated in 4 places ✓ 233880f
**Files:**
- `config.py:59-62` (tuple)
- `validator.py:19-22` (frozenset)
- `neo4j_store.py:20-23` (frozenset)
- `migration.py:18-21` (frozenset)

All four currently match (8 types). But any addition requires updating 4 files. If one drifts, validation accepts types that Neo4j rejects (or vice versa).

**Fix:** Single source of truth. Import from `config.py` or define in a shared constants module. The other three should reference it.

#### 4. tags.py defaults `type` to empty string instead of `semantic` ✓ 03dec29
**File:** `src/memoryschema/tags.py:75`
```python
type_val = root.get('type', '')
```
Schema says type defaults to `semantic` when omitted. Empty string is not a valid type. Entities parsed without an explicit type attribute get `type: ''` in the dict, which passes through to the store and could cause filtering issues.

**Fix:** Change to `root.get('type') or 'semantic'` (use `or` not default, since the attribute could be explicitly empty).

#### 5. Hook script silent failure when both stores fail ✓ 9e2e313
**File:** `src/memoryschema/hooks/hook-post-write.sh:85-98`

If both Neo4j and JSONL upserts fail, the Python block exits 0 (line 119 redirects stderr to /dev/null). The bash wrapper checks `$?` but it's 0, so the hook reports success. The memory file is written (L1a) but never indexed (L1b+).

**Fix:** Track whether indexing succeeded and `sys.exit(2)` if both fail. Remove `2>/dev/null` or make it conditional.

#### 6. `tomllib` import without Python 3.10 fallback ✓ 2a9cacb
**File:** `src/memoryschema/inheritance.py:12`
```python
import tomllib
```
`tomllib` is stdlib in Python 3.11+, but `pyproject.toml` says `requires-python = ">=3.10"`.

**Fix:** Either bump to `requires-python = ">=3.11"` or add fallback:
```python
try:
    import tomllib
except ImportError:
    import tomli as tomllib
```
and add `tomli; python_version < "3.11"` to dependencies.

---

### MEDIUM

#### 7. Duplicated scoring logic in store.py ✓ 4ac85fb
**File:** `src/memoryschema/store.py:320-360` (`_score_entry`) and `362-457` (`_score_all_entries`)

`_score_all_entries` reimplements the recency/importance/relevance formula inline for the numpy path (lines 392-412), duplicating `_score_entry`. The two can diverge — the numpy path hardcodes `w_r, w_i, w_v = 0.2, 0.3, 0.5` (semantic mode only, line 390), while `_score_entry` supports both modes.

**Fix:** Extract the weight selection and score computation into a shared helper.

#### 8. Upsert merges `filepath` and `schema` — unclear semantics ✓ 7757856
**File:** `src/memoryschema/store.py:119-122`

`filepath` is server-managed and `schema` version shouldn't change per-upsert, but both are in the merge loop. Not a bug today, but could cause confusion.

**Fix:** Document the policy or exclude them from the merge loop.

#### 9. `_derive_project` can produce invalid project names ✓ 4d784a3
**File:** `src/memoryschema/tags.py:17-39`

A path like `projects//child/` produces empty segments, creating invalid dot-notation. No validation after derivation.

**Fix:** After deriving, validate segments are non-empty and kebab-case before returning.

#### 10. Hook script stderr suppressed ✓ 9e2e313
**File:** `src/memoryschema/hooks/hook-post-write.sh:119`
```bash
" 2>/dev/null
```
All Python stderr is discarded, including parse errors (line 60: `sys.exit(2)`). The `sys.exit(2)` on parse failure works, but all debugging output is lost.

**Fix:** Redirect stderr to a log file or remove the suppression.

---

### LOW

#### 11. Dead imports in tags.py ✓ 70b8f5b
- Line 10: `import os` — unused
- Line 13: `from memoryschema.discovery import discover_memory_files` — unused

#### 12. F2 validation rule not implemented ✓ 19e6faf
Validator docstring references F1 and F3. F2 (directory scope validation) is mentioned in docs/schema.md but not implemented. This is intentional — memories don't have directory-based scope enforcement — but the docs should be updated to reflect this.

#### 13. `_score_all_entries` numpy path uses semantic mode only ✓ 4ac85fb
Line 390 hardcodes `w_r, w_i, w_v = 0.2, 0.3, 0.5`. The `mode` parameter in `_score_entry` is never passed through. All recalls use semantic weights even for structured queries.

---

## Findings Disproven by Verification

| Agent claim | Actual state |
|-------------|--------------|
| Hook calls undefined `compute_associations_single()` | Method exists at `neo4j_store.py:375` |
| `from_toml()` docstring wrong about env var priority | Env vars applied via `setattr` after construction (lines 128-138), docstring is correct |
| No integration tests for hierarchy in store | `TestHierarchyScoping` exists at `test_store.py:283-342` |
| Dead `os` import in tags.py | Agent said unused — need to verify (line 10) |

---

### DOCS

#### 14. Consolidate three plan docs into one ✓ 3038cb4
**Files to merge:**
- `docs/plan-hierarchical-nesting.md` (hierarchy.py, store scoping, relation types, CLI --project)
- `docs/plan-agent-inheritance.md` (inheritance.py, TOML config, rules resolution, CLI commands)
- `docs/plan-fix-6-inheritance-issues.md` (shared walker, overridden_rules, max_depth, validate_toml_name, doctor checks)

All three are marked COMPLETE. They represent a single feature area (agent hierarchy and inheritance) implemented across three sessions. Consolidate into `docs/plan-hierarchy-and-inheritance.md` with:
- **Context** — the problem (flat project field → nested agents with inheritance)
- **Architecture** — hierarchy.py (string ops) vs inheritance.py (filesystem), two matching modes, parent-absolute authority
- **Implementation summary** — what was built (modules, functions, relation types, CLI, store scoping)
- **Design decisions** — the key choices and why
- **Status: COMPLETE** header

Delete the three source files after creating the unified doc. No memory files reference them.

#### 15. Documentation sync pass (after all code fixes) ✓ 710dc70

After fixes 1-14 are applied, update all docs to reflect the new state. Changes are quantitative (counts, versions) and clarifying (type defaults, hook behavior), not structural.

**Files and specific updates:**

| File | Updates |
|------|---------|
| `docs/technical-reference.md` | Test count (390 → actual), doctor checks (20), test file count |
| `docs/implementation-guide.md` | Test count, doctor checks (20), hook reliability note |
| `README.md` | Test count, test file count, doctor checks (20) |
| `docs/system-overview.md` | Doctor checks (20) |
| `docs/schema.md` | Verify type default wording matches fix 4, verify F2 note matches fix 12 |
| `.claude/rules/memory-schema.md` | Sync with schema.md if Rule 3 (types) or Rule 4 (relations) changed |
| `src/memoryschema/templates/memory-schema.rules.tpl` | Sync with rules file |

**Search-and-replace targets:** `"390 tests"`, `"18 checks"`, `"25 test files"` — update all occurrences to actual post-fix counts.

This is the final item. No code fix should be considered done until its doc impact is reflected here.

---

## Verification Plan

After all fixes:
1. `python -m pytest tests/ -v` — all tests pass (count updated in docs)
2. `python -m pytest tests/ --co -q | tail -1` — get actual test count for doc updates
3. `python -c "from memoryschema import *"` — imports succeed on Python 3.10 (if fallback added)
4. `memoryschema doctor` — all checks pass (count updated in docs)
5. `grep -rn "390 tests\|18 checks\|25 test" docs/ README.md .claude/rules/` — no stale counts remain

## Status: COMPLETE

15/15 items implemented. 390 tests passing. 15 [S2] commits.
Session report: `docs/reports/2026-06-09-session-report-5.md`

Residuals:
- Neo4j max_depth not honored (architectural — Cypher can't call Python)
