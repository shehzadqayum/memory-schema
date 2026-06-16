# Package Memory System as Claude Code Plugin

## Context

The memory system is fully functional (113 entries, 7 spaces, 627 tests, content-agnostic) but integrated ad-hoc: hook in settings.json, rules in .claude/rules/, recall via Bash CLI. Packaging as a Claude Code plugin makes it installable, portable, and discoverable. No MCP server — hooks + rules + skills only.

## Architecture: Plugin is a wrapper, not a copy

The plugin contains ONLY configuration and instructions — not Python source code:

```
Plugin (.claude-plugin/)               Python package (pip-installed)
─────────────────────────              ────────────────────────────────
hooks/hooks.json  ──calls──▶           hook-post-write.sh ──imports──▶ memoryschema.*
hooks/hook-post-write.sh               (uses from memoryschema.tags, .store, etc.)
rules/*.md        ──loaded──▶ prompt
skills/*.md       ──invoke──▶          memoryschema CLI (recall, chain, status)

Data (per project or user-level)
────────────────────────────────
memory/MEMORY.md, store.jsonl, *.md  ◀──written by hook
```

**Prerequisite:** `pip install memory-schema` must be in the Python environment. The plugin references the installed package — it does not bundle or copy the source. The hook script calls `python3 -c "from memoryschema.* import ..."` which resolves to the pip-installed location.

**For development (editable install):** `pip install -e .` points to this repo's `src/memoryschema/`. The plugin's `.claude-plugin/` directory lives alongside `src/` in the same repo.

**For distribution:** Users install the pip package first, then install the plugin. The plugin discovers the package via the Python import system — no hardcoded paths.

## Prior Residuals (from [S4] 6e04215)

None.

## Phase 1 — Plugin manifest and structure ✓ fe45eca

### 1.1 Create plugin directory and manifest
Create `.claude-plugin/plugin.json`:
```json
{
  "name": "memory-schema",
  "version": "0.1.0",
  "description": "Content-agnostic memory system with 7-space embedding and variance-weighted retrieval",
  "author": {"name": "memory-schema"},
  "license": "MIT"
}
```

### 1.2 Create hooks/hooks.json
Register the PostToolUse Write hook. The hook script is the ONLY file that needs to exist in the plugin — it's a thin shell wrapper that imports from the pip-installed `memoryschema` package:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write",
      "hooks": [{
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/hook-post-write.sh",
        "timeout": 15
      }]
    }]
  }
}
```

The hook script (`hook-post-write.sh`) contains embedded Python that does `from memoryschema.tags import parse_memory_file`, `from memoryschema.store import MemoryStore`, etc. — all resolved via the pip-installed package, not local file paths.

**Option A (symlink):** Symlink `.claude-plugin/hooks/hook-post-write.sh` → `src/memoryschema/hooks/hook-post-write.sh` (avoids duplication during development).
**Option B (copy):** Copy the file (simpler for distribution, but requires keeping in sync).

Recommend Option A for development, Option B for release packaging.

### 1.3 Copy rules
Copy `.claude/rules/memory-schema.md` → `.claude-plugin/rules/memory-schema.md`
Copy `.claude/rules/memory-working.md` → `.claude-plugin/rules/memory-working.md`

### Key files
- `.claude-plugin/plugin.json` (new)
- `.claude-plugin/hooks/hooks.json` (new)
- `.claude-plugin/hooks/hook-post-write.sh` (copy from src/memoryschema/hooks/)
- `.claude-plugin/rules/*.md` (copy from .claude/rules/)

**Verification:** Plugin directory structure matches Claude Code plugin spec.

## Phase 2 — Skills ✓ cdd9e05

### 2.1 Create recall skill
`.claude-plugin/skills/recall/SKILL.md`:
- Model-invoked (Claude uses it automatically when user asks a question)
- Runs `memoryschema recall "<query>" --limit 3`
- Returns results as context for the response

### 2.2 Create chain management skills
- `.claude-plugin/skills/chain-start/SKILL.md` — wraps `memoryschema chain start <name>`
- `.claude-plugin/skills/chain-status/SKILL.md` — wraps `memoryschema chain status`
- `.claude-plugin/skills/chain-release/SKILL.md` — wraps `memoryschema chain release`

### 2.3 Create status skill
`.claude-plugin/skills/memory-status/SKILL.md` — wraps `memoryschema status`

### Key files
- `.claude-plugin/skills/recall/SKILL.md` (new)
- `.claude-plugin/skills/chain-start/SKILL.md` (new)
- `.claude-plugin/skills/chain-status/SKILL.md` (new)
- `.claude-plugin/skills/chain-release/SKILL.md` (new)
- `.claude-plugin/skills/memory-status/SKILL.md` (new)

**Verification:** Skills discoverable via `/recall`, `/chain-start`, etc.

## Phase 3 — Hybrid memory scope ✓ 8c35244

### 3.1 Update hook for hybrid data path
Modify hook-post-write.sh to:
- Write to project's `memory/` if it exists
- Fall back to `~/.claude/memory/` if no project memory dir
- Derive project root from file path (existing logic) or use `~/.claude/` as fallback

### 3.2 Update recall for dual-store search
Modify the recall skill to:
- Search project store first
- Then search user-level store (`~/.claude/memory/store.jsonl`)
- Merge and re-rank results

### Key files
- `.claude-plugin/hooks/hook-post-write.sh` (modify)
- `.claude-plugin/skills/recall/SKILL.md` (modify)

**Verification:** Write a memory in a project → appears in project store. Write without a project → appears in ~/.claude/memory/. Recall finds entries from both stores.

## Phase 4 — Documentation and installation ✓ 7971ca6

### 4.1 Plugin README
Create `.claude-plugin/README.md` with:
- What it does
- Prerequisites: `pip install memory-schema` (the plugin is a wrapper, not the code)
- Installation: `/plugin install memory-schema` or local dev install
- Environment: `VOYAGE_API_KEY` for embeddings (optional — system degrades to text search)
- Quick start: write a memory, recall it, start a chain
- Architecture note: plugin = hooks + rules + skills, code = pip package

### 4.2 Update project README
Add plugin installation section to the main README.md.

### Key files
- `.claude-plugin/README.md` (new)
- `README.md` (update)

**Verification:** Plugin installable, hook fires on write, recall works, chain lifecycle works.

## Verification Criteria

| # | Criterion | Phase | Status type |
|---|-----------|-------|-------------|
| 1 | Plugin manifest valid, directory structure correct | 1 | Tested |
| 2 | Hook fires on Write to memory/*.md (same as current) | 1 | Operative |
| 3 | Skills discoverable and executable (/recall, /chain-start, etc.) | 2 | Operative |
| 4 | Hybrid scope: project store + user-level fallback | 3 | Operative |
| 5 | README documents installation and quick start | 4 | Tested |
