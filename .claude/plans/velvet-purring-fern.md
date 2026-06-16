# Bootstrap Skill — Project Knowledge Map Generator

## Context

After `memoryschema init`, the memory store is empty. The user wants a `/bootstrap` skill that systematically reads a project's documentation and source code, then creates interconnected memory entities forming a knowledge graph. This gives the memory system a head start — future sessions have project context from the first recall.

The skill is a procedure document (SKILL.md) that instructs Claude what to do. Claude follows the steps, reads files, and writes `memory/*.md` files. The PostToolUse Write hook handles indexing automatically (parse → embed 7 spaces → gate → store).

## Prior Residuals (from [S4] 59b653b)

- `plugin_cmd.py` has no test coverage (low impact — deferred)

## Phase 1 — Create the bootstrap skill

### 1.1 Create SKILL.md

Create `.claude-plugin/skills/bootstrap/SKILL.md` with a 7-phase procedure:

**Phase 0 — Preflight:**
- Verify `memoryschema status` works (confirms init was run)
- Release any active chain, then `memoryschema chain start "chain-bootstrap"`
- Detect project name from `memoryschema.toml` (fallback: directory name)
- Recall existing bootstrap entities (idempotent re-run check)

**Phase 1 — Project Overview:**
- Read README, package manifest (pyproject.toml / package.json / Cargo.toml / go.mod / etc.)
- Write `memory/bootstrap-project-overview.md` (importance 8)
- Update chain entity

**Phase 2 — Directory Structure:**
- Scan source files (`find` with common extensions, capped at 200 results)
- Identify source dirs, test dirs, doc dirs
- Write `memory/bootstrap-directory-structure.md` (importance 7)
- Determine project size tier: small (<5 dirs), medium (5-15), large (>15)

**Phase 3 — Tech Stack:**
- Parse dependencies from manifest found in Phase 1
- Identify runtime vs dev deps, key frameworks
- Write `memory/bootstrap-tech-stack.md` (importance 7)

**Phase 4 — Configuration:**
- Read .env.example, config files, Docker files, Makefile
- Identify required env vars and build steps
- Write `memory/bootstrap-configuration.md` (importance 6)

**Phase 5 — Module Deep Dive** (scaled to project size):
- Small: read every source file's first 50 lines, one entity per directory
- Medium: read entry point / index files only, one entity per top-level dir
- Large: top 15 most significant modules only, rest noted in architecture entity
- Write `memory/bootstrap-module-<name>.md` per module (importance 6-7)
- Each has `DEPENDS_ON bootstrap-project-overview` + `USES` for inter-module deps

**Phase 6 — Architecture and API Surface:**
- Synthesize patterns: error handling, naming conventions, architectural patterns
- Identify public API: endpoints, CLI commands, exported functions
- Write `memory/bootstrap-architecture-patterns.md` (importance 8)
- Write `memory/bootstrap-api-surface.md` (importance 7)

**Phase 7 — Release and Report:**
- Append "Conclusion:" observation to chain, release with `memoryschema chain release`
- Run `memoryschema status` to show final count
- Present summary: entities created, relation graph, total coverage

**Entity budget:** 8-22 entities total (1 chain + 7 structural + up to 15 modules). Cap prevents noise in small stores.

**Entity naming:** All use `bootstrap-` prefix (chain uses `chain-bootstrap`). Deterministic names enable idempotent re-runs via upsert.

**Relation graph:**
```
bootstrap-project-overview  (hub)
  ← DEPENDS_ON  bootstrap-directory-structure
  ← DEPENDS_ON  bootstrap-tech-stack
  ← DEPENDS_ON  bootstrap-configuration
  ← DEPENDS_ON  bootstrap-architecture-patterns
  ← DEPENDS_ON  bootstrap-api-surface
  ← DEPENDS_ON  bootstrap-module-*

bootstrap-module-auth  ─USES→  bootstrap-module-database
bootstrap-api-surface  ─USES→  bootstrap-module-api
bootstrap-architecture-patterns  ─INFORMS→  bootstrap-module-*
chain-bootstrap  ─USES→  all bootstrap entities
```

### Key files
- `.claude-plugin/skills/bootstrap/SKILL.md` (new)

## Phase 2 — Register and deploy

### 2.1 Add to plugin deploy
Add `("skills/bootstrap/SKILL.md", "skills/bootstrap/SKILL.md")` to `SKILL_FILES` in `src/memoryschema/cli/plugin_cmd.py` (line 18).

### 2.2 Deploy to user level
Run `memoryschema plugin deploy --force` to copy the new skill to `~/.claude/skills/bootstrap/SKILL.md`.

### Key files
- `src/memoryschema/cli/plugin_cmd.py` (modify line 18)

## Phase 3 — Documentation

### 3.1 Update plugin README
Add `/bootstrap` to the skills table in `.claude-plugin/README.md` (line 56).

### 3.2 Update project README
Add `/bootstrap` to the Claude Code Plugin skills table in `README.md`.

### 3.3 CHANGELOG
Add entry under `[Unreleased] > Added (Claude Code Plugin)`.

### Key files
- `.claude-plugin/README.md` (modify)
- `README.md` (modify)
- `CHANGELOG.md` (modify)

## Verification

1. **Skill exists:** `cat ~/.claude/skills/bootstrap/SKILL.md | head -5` shows the skill header
2. **Skill discoverable:** Claude sees `/bootstrap` in the skills list after deploy
3. **Tests pass:** `python3 -m pytest tests/ -x -q` — 627 passing (no test changes, skill is a doc file)
4. **Manual test:** Run `memoryschema init` in a test project, then invoke `/bootstrap` and verify entities are created in `memory/` and indexed in `store.jsonl`
