# Post-v4 Full Documentation Alignment

## Context

After completing the v4 verification axis plan (sessions 13-16, 472→569 tests), a file-by-file audit of every source file, CLI command, template, and documentation surface found ~40 discrepancies. The Phase 8 doc sweep updated version labels and added new features to some tables, but missed schema="3" in code examples, stale test counts, missing server-managed fields, missing basis factor in scoring docs, write gate still described as "four-stage", and several CLI/module docstring updates.

## Prior Residuals (from [S4] 97553d0)

None.

## Phase 1-5 — All fixes (single commit) ✓ 5513f7e

### 1A. validate_cmd.py docstring
- Line 14: "V1-V13" → "V1-V14"

### 1B. main.py docstring — add force + decline
- Add under appropriate section: force, decline commands

### 1C. store.py docstring — add v4 specifics
- Add: basis upgrade, verification guard, MITIGATES dampening, force records

### 1D. neo4j_store.py docstring — add v4 specifics
- Add: JSON-per-element model, basis factor, verification guard

### 1E. __init__.py — consider v4 exports
- Observation, observation_text, serialize_observation, deserialize_observation
- VALID_BASES, VERIFICATION_RANKS (if public API desired)

## Phase 2 — schema="3" → schema="4" everywhere

### 2A. docs/schema.md: lines 24, 32, 58 (entity examples + required field table)
### 2B. docs/technical-reference.md: line 5 ("v3"→"v4"), line 37 (example)
### 2C. README.md: line 145 (example)
### 2D. .claude/rules/memory-schema.md: line 1 "(v3)"→"(v4)", line 18 "Current: 3"→"4", lines 25+33 (examples)
### 2E. src/memoryschema/templates/memory-schema.rules.tpl: same as 2D (keep in sync)
### 2F. docs/system-overview.md: line 15 (example)
### 2G. docs/implementation-guide.md: line 155 (test example)
### 2H. docs/hierarchy-and-inheritance.md: line 10 "Schema is v3" → "v4"

## Phase 3 — Test counts 472→569, 27→33 files

### 3A. docs/technical-reference.md: line 272 + test category table
### 3B. README.md: line 312 + category table (lines 314-320)
### 3C. docs/implementation-guide.md: line 147

## Phase 4 — Missing v4 features in schema.md

### 4A. Server-managed fields table: add verified_at, generator, embed_model
### 4B. Relation count intro: "Eight" → "Nine (seven active, two deprecated)"
### 4C. Full entity example: add basis="measured" on an observation
### 4D. Scoring section: add basis factor (measured=1.0, inferred=0.97, reported=0.93)
### 4E. Write gate: "four-stage" → "six-stage"; add stages 5-6 to pipeline table
### 4F. On Reflect: add contradiction-aware behavior (skip + --include-contradictory)

## Phase 5 — Missing v4 features in other docs

### 5A. technical-reference.md scoring: add basis factor
### 5B. technical-reference.md config table: add ~7 v4 fields (generator_id, numeric_probe_*, verification_staleness_days, l0_echo_threshold, mitigation_dampening)
### 5C. technical-reference.md tags module: "(v2: prompt + reasoning)" → "(v4: basis on observations)"
### 5D. .claude/rules/memory-schema.md Rule 7 scoring: add basis factor
### 5E. src/memoryschema/templates/memory-schema.rules.tpl: same as 5D
### 5F. TOML template: add commented v4 gate config section

## Verification

1. `python -m pytest tests/ -v` — 569 pass
2. `grep -rn 'schema="3"' src/ docs/ .claude/ README.md | grep -v test | grep -v __pycache__ | grep -v plans/ | grep -v memory/ | grep -v reports/` — zero
3. `grep -rn "472 test\|27 file\|27 test" docs/ README.md | grep -v plans/ | grep -v reports/ | grep -v memory/` — zero
4. `grep -rn "V1-V13" src/ docs/ .claude/ | grep -v __pycache__ | grep -v plans/` — zero
5. `grep -rn "four-stage\|four stage" docs/` — zero
6. `diff .claude/rules/memory-schema.md src/memoryschema/templates/memory-schema.rules.tpl` — identical
