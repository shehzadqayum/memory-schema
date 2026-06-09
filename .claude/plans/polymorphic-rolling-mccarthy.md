# Hierarchy & Inheritance: Reference Doc + Documentation Alignment

## Context

Two problems: (1) hierarchy and inheritance features lack a standalone reference doc — information is scattered across 5 files. (2) A cross-doc alignment audit found 7 mismatches between documentation and implementation that need fixing alongside the new doc.

## Prior Residuals (from [S4] 98cf53f)

- R1: Neo4j max_depth not honored — Cypher can't call Python → deferring (architectural limitation, not docs scope)

## Items

### Item 1: Create `docs/hierarchy-and-inheritance.md` ✓ 4a569d8

New standalone reference document with sections:

1. **Overview** — two features, two modules, backward compatible
2. **Project Hierarchy** — naming convention, when to use, directory structure
3. **Memory Visibility** — scope vs filter modes, visibility truth table, max_depth, Neo4j limitation
4. **Configuration Inheritance** — resolution order, TOML format, 4 worked examples
5. **Rules Inheritance** — algorithm, conflict example, grandparent-wins, design rationale
6. **CLI Operations** — scoped recall/search, config --chain, rules --conflicts, doctor checks (with sample output)
7. **Python API Reference** — signature tables for hierarchy.py (9 functions) and inheritance.py (10 functions)
8. **Troubleshooting** — 9-row table covering common issues
9. **Design Decisions** — 6 key architectural choices

Source: `hierarchy.py`, `inheritance.py`, `config.py`, `store.py`, `neo4j_store.py`, CLI commands

### Item 2: Move plan doc to history ✓ 7ab18ef

- Create `docs/plans/` directory
- Move `docs/plan-hierarchy-and-inheritance.md` → `docs/plans/`
- Add superseded note at top

### Item 3: Fix doctor check in doctor_cmd.py ✓ fe39afe

**File:** `src/memoryschema/cli/doctor_cmd.py:36`
`ok = v >= (3, 10)` → `ok = v >= (3, 11)` and update message to "Upgrade to Python 3.11+"

This aligns the runtime check with `pyproject.toml` (`requires-python = ">=3.11"`).

### Item 4: Fix stale counts in tech-ref and impl-guide ✓ 760381c

**`docs/technical-reference.md:191`:** "18 live checks" → "20 live checks"
**`docs/implementation-guide.md:136`:** "Checks 18 components" → "Checks 20 components"

(system-overview.md already says 20 — correct)

### Item 5: Fix `memory/user/` phantom path in schema.md ✓ aad052a

**`docs/schema.md:188`:**
Remove `memory/user/<name>.md` — this path convention doesn't exist in code. All memories live in `memory/<name>.md`. Scoping is via the `<memory:project>` element.

### Item 6: Fix working memory importance in system-overview.md ✓ b510d4e

**`docs/system-overview.md:35`:** "Importance 8-10" → "Importance 10"
Matches `.claude/rules/memory-working.md` which says "All working memory entities MUST use importance **10**."

### Item 7: Add scoring bonuses to schema.md ✓ 95dfb1c

The retrieval scoring formula omits two bonuses implemented in `store.py`:
- Hub bonus: `+0.05 * min(backlinks, 5)` (store.py:378)
- Text match boost: `+0.1` if query substring found

Add these to the scoring section in schema.md. Sync to rules file and template.

### Item 8: Cross-reference updates ✓ d175037

Add forward references to the new doc from:
- `README.md` — documentation list + architecture section
- `docs/system-overview.md` — after Agent Hierarchy section
- `docs/technical-reference.md` — from hierarchy/inheritance module rows
- `docs/implementation-guide.md` — after Nested Agent Setup section

### Item 9: CHANGELOG + template sync ✓ 8302dd6

- CHANGELOG: Add reference doc, plan move, alignment fixes
- Sync `.claude/rules/memory-schema.md` ↔ `templates/memory-schema.rules.tpl` if scoring section changed

## Files

| Action | File |
|--------|------|
| Create | `docs/hierarchy-and-inheritance.md` |
| Create | `docs/plans/` directory |
| Move | `docs/plan-hierarchy-and-inheritance.md` → `docs/plans/` |
| Modify | `src/memoryschema/cli/doctor_cmd.py` (Python version check) |
| Modify | `docs/technical-reference.md` (doctor count) |
| Modify | `docs/implementation-guide.md` (doctor count) |
| Modify | `docs/schema.md` (remove user/ path, add scoring bonuses) |
| Modify | `docs/system-overview.md` (importance, forward ref) |
| Modify | `.claude/rules/memory-schema.md` (scoring bonuses) |
| Modify | `src/memoryschema/templates/memory-schema.rules.tpl` (sync) |
| Modify | `README.md` (forward refs) |
| Modify | `CHANGELOG.md` |

## Verification

1. `python -m pytest tests/` — all pass
2. New doc covers all functions from `hierarchy.py` and `inheritance.py`
3. `grep -rn "18 checks\|3\.10\|memory/user/" docs/ README.md .claude/rules/ src/memoryschema/templates/` — no stale references
4. `grep -rn "plan-hierarchy-and-inheritance" docs/ README.md` — no broken references to moved file
5. Rules file and template in sync: `diff .claude/rules/memory-schema.md src/memoryschema/templates/memory-schema.rules.tpl`

## Status: COMPLETE

9/9 items implemented. 390 tests passing. 9 [S2] commits.
Session report: `docs/reports/2026-06-09-session-report-6.md`

Residuals:
- Neo4j max_depth not honored (carried from session 5 — architectural)
