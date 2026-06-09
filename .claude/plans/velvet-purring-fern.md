# Full Documentation Alignment ✓ b3226f3

## Context

All documentation is stale after 3 sessions of feature work. hierarchy.py (9 functions), inheritance.py (10 functions), PARENT_OF/CHILD_OF relation types, TOML config, new CLI commands, --project scoping, and 20/20 doctor checks are implemented but undocumented. This covers ALL documentation — user-facing docs, templates, rules, examples, and completed plan files.

## Prior Residuals (from [S4] bb6de28)

None.

## Items

### Item 1: docs/schema.md
- Add PARENT_OF, CHILD_OF to Relation Types table
- New section "Dot-Notation Project Hierarchy" — naming, ancestor/descendant, examples
- New section "Hierarchy Scoping" — bidirectional (recall) vs subtree-only (search/list), max_depth, unscoped entity visibility

### Item 2: docs/system-overview.md
- New "Agent Hierarchy" section — projects as agents, containment model, shared memory
- New "Configuration Inheritance" section — TOML chain, resolution order (env > CLI > parent TOML > child TOML > defaults), parent-absolute authority
- New "Rules Inheritance" section — parent wins on conflict, child adds unique, conditional autonomy

### Item 3: docs/technical-reference.md
- Add `memoryschema.hierarchy` module with all public functions
- Add `memoryschema.inheritance` module with all public functions
- Add `MemoryConfig.from_toml()`, `config_file_path`, `project_segments`, `parent_project_name`
- Add `memoryschema rules` and `memoryschema config` CLI commands
- Update test count to 390, doctor to 20/20

### Item 4: docs/implementation-guide.md
- Add TOML configuration step after init
- Add nested agent setup example (parent + child with TOML files)
- Add `memoryschema config --chain` and `memoryschema rules --conflicts` to verification

### Item 5: README.md
- Update intro for hierarchical agent support
- Add "TOML Configuration" subsection after "Initialize Project"
- Add `memoryschema rules`, `memoryschema config` to CLI Reference
- Add `--project` to recall/search entries
- Add "Hierarchical Inheritance" to Architecture section
- Update counts (390 tests, 20/20 doctor)

### Item 6: .claude/rules/memory-schema.md + template
- Update Rule 4: add PARENT_OF, CHILD_OF with semantics
- Add hierarchy scoping note after Rule 4
- Update `src/memoryschema/templates/memory-schema.rules.tpl` to match (source for `init`)

### Item 7: Completed plan files — mark historical
- `docs/plan-hierarchical-nesting.md` — add "Status: COMPLETE" header
- `docs/plan-agent-inheritance.md` — add "Status: COMPLETE" header
- `docs/plan-fix-6-inheritance-issues.md` — add "Status: COMPLETE" header

### Item 8: CLI self-documentation alignment
- `src/memoryschema/cli/main.py` top-level docstring: add "Diagnostics & Inheritance" section listing `rules`, `config` commands
- `src/memoryschema/cli/main.py` `init` docstring: mention `memoryschema.toml` generation
- `src/memoryschema/cli/doctor_cmd.py` `doctor` docstring: mention toml_config and rules_inherit checks

## Files to Modify

| File | Change |
|------|--------|
| `docs/schema.md` | PARENT_OF/CHILD_OF, dot-notation, scoping sections |
| `docs/system-overview.md` | Agent hierarchy, config inheritance, rules inheritance |
| `docs/technical-reference.md` | hierarchy.py, inheritance.py, new CLI, counts |
| `docs/implementation-guide.md` | TOML step, nested agent example |
| `README.md` | Hierarchy intro, TOML, CLI commands, architecture, counts |
| `.claude/rules/memory-schema.md` | PARENT_OF/CHILD_OF in Rule 4 |
| `src/memoryschema/templates/memory-schema.rules.tpl` | Same Rule 4 update |
| `docs/plan-hierarchical-nesting.md` | Status: COMPLETE header |
| `docs/plan-agent-inheritance.md` | Status: COMPLETE header |
| `docs/plan-fix-6-inheritance-issues.md` | Status: COMPLETE header |
| `src/memoryschema/cli/main.py` | Top-level + init docstrings |
| `src/memoryschema/cli/doctor_cmd.py` | Doctor docstring |

## Verification

1. Relation types tables have 8 entries everywhere ✓
2. CLI reference lists `rules`, `config`, `--project` ✓
3. `memoryschema --help` shows Diagnostics section ✓
4. `memoryschema init --help` mentions TOML ✓
5. `memoryschema doctor --help` mentions 20-point ✓
6. Test count 390, doctor 20/20 in all docs ✓
7. Template and rules file in sync ✓
8. 390 tests passing ✓

## Status: COMPLETE

Session report: `docs/reports/2026-06-09-session-report-4.md`
