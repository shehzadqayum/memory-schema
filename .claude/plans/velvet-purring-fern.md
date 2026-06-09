# Documentation Update: Hierarchy & Inheritance

## Context

All documentation is stale after 3 sessions of feature work. hierarchy.py (9 public functions), inheritance.py (10 public functions), PARENT_OF/CHILD_OF relation types, TOML config, `memoryschema rules`, `memoryschema config`, `--project` on recall/search, and 20/20 doctor checks are implemented but undocumented. CHANGELOG is the only current doc.

## Prior Residuals (from [S4] bb6de28)

None.

## Items

### Item 1: docs/schema.md — Add hierarchy + new relation types

- Add PARENT_OF, CHILD_OF to Relation Types table (after existing 6)
- Add new section "Dot-Notation Project Hierarchy" — naming convention, ancestor/descendant, examples
- Add new section "Hierarchy Scoping" — bidirectional (recall) vs subtree-only (search/list), max_depth, unscoped entity visibility

### Item 2: docs/system-overview.md — Add agent model + inheritance

- Add "Agent Hierarchy" section — projects as agents, parent contains child, shared memory space
- Add "Configuration Inheritance" section — TOML chain, resolution order diagram (env > CLI > parent TOML > child TOML > defaults), parent-absolute authority
- Add "Rules Inheritance" section — parent wins on filename conflict, child adds unique rules, conditional autonomy when parent absent

### Item 3: docs/technical-reference.md — Add module references

- Add `memoryschema.hierarchy` module entry with all public functions
- Add `memoryschema.inheritance` module entry with all public functions
- Add `MemoryConfig.from_toml()`, `config_file_path`, `project_segments`, `parent_project_name` to config docs
- Add `memoryschema rules` and `memoryschema config` to CLI commands
- Update test count: 390

### Item 4: docs/implementation-guide.md — Add TOML + nested agents

- Add step for TOML configuration after init
- Add example of nested agent setup (parent + child directories with TOML files)
- Add `memoryschema config --chain` and `memoryschema rules --conflicts` to verification

### Item 5: README.md — Add hierarchy features to all sections

- Update intro to mention hierarchical agent support
- Add "TOML Configuration" subsection after "Initialize Project"
- Add `memoryschema rules` and `memoryschema config` to CLI Reference
- Add `--project` option to recall/search entries
- Add "Hierarchical Inheritance" to Architecture section
- Update test count and doctor count (390 tests, 20/20)

### Item 6: .claude/rules/memory-schema.md — Add PARENT_OF, CHILD_OF

- Update Rule 4 Relations table: add PARENT_OF and CHILD_OF with semantics
- Add note about hierarchy scoping behavior after Rule 4

## Files to Modify

| File | Change |
|------|--------|
| `docs/schema.md` | PARENT_OF/CHILD_OF, dot-notation, scoping sections |
| `docs/system-overview.md` | Agent hierarchy, config inheritance, rules inheritance |
| `docs/technical-reference.md` | hierarchy.py, inheritance.py modules, new CLI, test count |
| `docs/implementation-guide.md` | TOML step, nested agent example |
| `README.md` | Hierarchy intro, TOML config, CLI commands, architecture |
| `.claude/rules/memory-schema.md` | PARENT_OF/CHILD_OF in Rule 4 |

## Verification

1. All doc files reference current module names and function signatures
2. Relation types table has 8 entries (6 original + PARENT_OF + CHILD_OF)
3. CLI reference lists `rules`, `config`, `--project` on recall/search
4. Test count is 390, doctor is 20/20 in all docs
5. `python -m pytest tests/ -v` — still 390 passing (docs-only changes)
