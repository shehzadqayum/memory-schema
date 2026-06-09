# Full v3 Documentation Alignment

## Context

Exhaustive audit found v3 implementation complete but documentation stuck at v2. Schema version, validation rules, relation type deprecation, working memory policy, doctor/test counts, and module listings all diverge from implementation.

## Prior Residuals (from [S4] f879282)

None.

## Findings (15 items)

### CRITICAL — Schema & Rules mismatch
1. docs/schema.md: claims v2, impl is v3; missing status/provenance attributes
2. docs/schema.md: validation rules only V1-V10, R1-R5; missing V11 (status), V12 (provenance), R6 (referential integrity)
3. docs/schema.md: lists PARENT_OF/CHILD_OF as active; should be flagged deprecated
4. .claude/rules/memory-schema.md: same v2 issues (synced from template)
5. src/memoryschema/templates/memory-schema.rules.tpl: same v2 issues (source for init)

### CRITICAL — Working memory policy
6. README.md: claims "every response writes memory"; actual policy is selective-write
7. docs/implementation-guide.md: same "every response" claims
8. docs/system-overview.md: check if working memory description matches selective-write

### NUMERIC — Counts stale
9. Test count: docs say 390, actual is 432 across 28 files (README, tech-ref, impl-guide)
10. Doctor count: README says 18 and 20 in different places; tech-ref says 20; actual is 21
11. README test breakdown (120+46+23+73=262) doesn't match 390 or 432

### MODULES — Missing from technical reference
12. docs/technical-reference.md: missing audit.py, l0_budget.py, write_gate.py, eval_cmd.py, reflect_cmd.py

### CLI — Minor gaps
13. docs/technical-reference.md: missing reflect command in usage examples
14. main.py docstring: verify doctor says "21-point" not "20-point"

### TEMPLATE — Template sync
15. Both templates and rules files match each other but are v2; need v3 update to both simultaneously

## Fix Items

### Item 1: docs/schema.md — v3 upgrade
- Schema version 2→3
- Add status attribute (active/superseded/archived/quarantined)
- Add provenance attribute (first-party/user/ingested/derived)
- Mark PARENT_OF, CHILD_OF as deprecated (accepted on read, warned on write)
- Add V11 (status validation), V12 (provenance validation), R6 (referential integrity)
- Remove F2 if still listed (never implemented)

### Item 2: .claude/rules/memory-schema.md + template — v3 sync
- Same v3 changes as Item 1
- Update both files simultaneously (template is source for init)
- Verify byte-for-byte match after update

### Item 3: README.md — counts + policy
- Working memory: "every response" → selective-write reference
- Test count: 390→432, 28 files
- Doctor count: consistent 21/21 everywhere
- Test breakdown table: update to match 432
- Architecture: mention schema v3, status, provenance

### Item 4: docs/technical-reference.md — modules + counts
- Add modules: audit.py, l0_budget.py, write_gate.py, eval_cmd.py, reflect_cmd.py
- Test count: 390→432, 28 files
- Doctor count: 20→21
- Add reflect to CLI usage examples
- Update test breakdown table

### Item 5: docs/implementation-guide.md — policy + counts
- Working memory: remove "every response MUST write" references
- Test count: update
- Doctor count: update
- Python version: verify says 3.11+

### Item 6: docs/system-overview.md — policy + counts
- Working memory description: verify matches selective-write
- Doctor count: verify says 21
- Test count: update if mentioned

### Item 7: main.py docstring — doctor label
- "20-point" → "21-point" if stale

## Files to Modify

| File | Changes |
|------|---------|
| `docs/schema.md` | v3 upgrade: version, status, provenance, deprecated relations, V11/V12/R6 |
| `.claude/rules/memory-schema.md` | v3 sync (same as schema.md Rule changes) |
| `src/memoryschema/templates/memory-schema.rules.tpl` | v3 sync (source for init) |
| `README.md` | Test/doctor counts, working memory policy, architecture v3 |
| `docs/technical-reference.md` | Missing modules, test/doctor counts, reflect |
| `docs/implementation-guide.md` | Working memory policy, counts |
| `docs/system-overview.md` | Policy, counts verification |
| `src/memoryschema/cli/main.py` | Doctor label if stale |

## Verification

1. Schema version "3" in schema.md, rules, and template
2. V11, V12, R6 documented in schema.md
3. PARENT_OF/CHILD_OF marked deprecated everywhere
4. No "every response MUST write" in any doc
5. Test count 432 everywhere
6. Doctor count 21 everywhere
7. Template matches rules file
8. `python -m pytest tests/ -v` — 432 passing
