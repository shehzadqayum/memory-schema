# Chain Enforcement: Edit-not-Write + Stop Hook Reminder

## Context

Two issues discovered during active use of the memory system:

1. **No enforcement of chain updates** — Rules say "update chain every response" but nothing enforces it. Claude can deliver an entire session without updating the chain, and the rules are purely advisory.
2. **Write overwrites chain files** — Using `Write` to update a chain entity replaces the entire `.md` file. If a prior observation is omitted from the rewrite, it's permanently lost from disk. The JSONL/Neo4j upsert merge semantics protect the index layer, but the `.md` file is the authoritative source.

A working prototype exists at `/Volumes/RAID0/Users/shehzad/Projects/karpathy-llm-wiki/.claude/settings.local.json` — it uses a PostToolUse sentinel touch + Stop hook reminder. This plan upstreams that prototype into the memory-schema package properly.

Single source of truth is the package at `/Volumes/RAID0/Users/shehzad/Claude/packages/memory-schema/`.

## Prior Residuals (from [S4] ebdc331)

- R1: `plugin_cmd.py` has no test coverage (source: session 24) → deferring (this plan updates matchers in plugin_cmd.py but comprehensive deploy/uninstall/status test coverage is a separate effort)

## Pre-existing state

- `hook-post-write.sh` has uncommitted `python3` → `$PYTHON` changes — fold into Phase 1.
- `~/.claude/settings.json` has stale skills/ict/fos Write hooks (per disabled-hooks memory) — separate issue, not in scope.

---

## Phase 1 — Widen hook matcher to `Write|Edit` + sentinel touch ✓ 9048165

### 1.1 hook-post-write.sh

**File:** `src/memoryschema/hooks/hook-post-write.sh`

- Line 3: comment → "Triggered by Claude Code after every Write or Edit tool call."
- Line 24: `if [ "$TOOL_NAME" != "Write" ]` → `if [ "$TOOL_NAME" != "Write" ] && [ "$TOOL_NAME" != "Edit" ]`
- After line 33 (after memory-file filter, before MEMORY.md skip): add sentinel touch:
  ```bash
  # Touch sentinel so Stop hook knows a memory file was updated this response
  touch /tmp/claude-memory-chain-updated 2>/dev/null || true
  ```
- Folds in existing uncommitted `$PYTHON` changes (lines 15, 21, 28, 41).

### 1.2 hooks.json

**File:** `.claude-plugin/hooks/hooks.json`

- Line 5: `"matcher": "Write"` → `"matcher": "Write|Edit"`

### 1.3 hook_cmd.py (4 locations)

**File:** `src/memoryschema/cli/hook_cmd.py`

| Line | Current | New |
|------|---------|-----|
| 77 | `== "Write"` | `in ("Write", "Write|Edit")` |
| 85 | `"matcher": "Write"` | `"matcher": "Write|Edit"` |
| 124 | `== "Write"` | `in ("Write", "Write|Edit")` |
| 166 | `== "Write"` | `in ("Write", "Write|Edit")` |

The `in ("Write", "Write|Edit")` pattern gives backward compat — existing installs with old `"Write"` matcher are still found by `uninstall`/`status`.

### 1.4 plugin_cmd.py (3 locations)

**File:** `src/memoryschema/cli/plugin_cmd.py`

| Line | Function | Current | New |
|------|----------|---------|-----|
| 93 | `_hook_already_registered` | `== "Write"` | `in ("Write", "Write|Edit")` |
| 108 | `_add_hook` | `"matcher": "Write"` | `"matcher": "Write|Edit"` |
| 125 | `_remove_hook` | `== "Write"` | `in ("Write", "Write|Edit")` |

### 1.5 doctor_cmd.py

**File:** `src/memoryschema/cli/doctor_cmd.py`

- Line 264: `== "Write"` → `in ("Write", "Write|Edit")`

### 1.6 main.py (cosmetic)

**File:** `src/memoryschema/cli/main.py`

- Line 213: init example `"matcher": "Write"` → `"matcher": "Write|Edit"`

### 1.7 Tests

**File:** `tests/test_cli_hook.py`

- Lines 28, 55, 70: update fixture `"matcher": "Write"` → `"matcher": "Write|Edit"`
- Line 49: add assertion that installed entry has `"matcher": "Write|Edit"`
- New test: `test_status_detects_legacy_write_matcher` — verify `status` finds old `"Write"` matcher (backward compat)

### Verify Phase 1

```bash
pytest tests/test_cli_hook.py -v
echo '{"tool_name":"Edit","tool_input":{"file_path":"memory/test.md"}}' | bash src/memoryschema/hooks/hook-post-write.sh
# ^ should not exit early (passes tool_name filter)
echo '{"tool_name":"Read","tool_input":{"file_path":"memory/test.md"}}' | bash src/memoryschema/hooks/hook-post-write.sh
# ^ should exit 0 immediately (filtered out)
```

---

## Phase 2 — Stop hook script + registration ✓ 0423a40

### 2.1 New Stop hook script

**New file:** `src/memoryschema/hooks/hook-stop.sh`

```bash
#!/bin/bash
# Stop hook: reminds Claude to update the active chain if no memory write
# happened this response. Works with hook-post-write.sh which touches the
# sentinel on every memory file write.

set -uo pipefail

CHAIN_FILE="memory/.active_chain"
SENTINEL="/tmp/claude-memory-chain-updated"

# No active chain — nothing to remind
if [ ! -f "$CHAIN_FILE" ]; then
    echo '{}'
    exit 0
fi

CHAIN_NAME=$(cat "$CHAIN_FILE" | tr -d '[:space:]')

# Chain was updated this response — clear sentinel
if [ -f "$SENTINEL" ]; then
    rm -f "$SENTINEL"
    echo '{}'
    exit 0
fi

# Chain active but not updated — inject reminder
echo "{\"hookSpecificOutput\":{\"hookEventName\":\"Stop\",\"additionalContext\":\"MEMORY CHAIN REMINDER: The active chain \\\"$CHAIN_NAME\\\" was NOT updated this response. Edit memory/$CHAIN_NAME.md now (use Edit, not Write).\"}}"
exit 0
```

### 2.2 hooks.json — add Stop entry

**File:** `.claude-plugin/hooks/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/hook-post-write.sh",
          "timeout": 15
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/hook-stop.sh",
          "timeout": 5
        }]
      }
    ]
  }
}
```

### 2.3 hook_cmd.py — Stop hook install/uninstall/status

**File:** `src/memoryschema/cli/hook_cmd.py`

- Add `_stop_hook_script_path()` resolving `memoryschema.hooks/hook-stop.sh`
- `install()`: after registering PostToolUse, also register Stop hook in `settings["hooks"].setdefault("Stop", [])`
- `uninstall()`: also remove Stop hook entries containing `hook-stop.sh`
- `hook_status()`: also check and report Stop hook registration

### 2.4 plugin_cmd.py — Stop hook deploy/uninstall

**File:** `src/memoryschema/cli/plugin_cmd.py`

- `_add_hook()`: also add Stop hook entry
- `_remove_hook()`: also remove Stop hook entries
- `_hook_already_registered()`: also check Stop hook
- `deploy()`, `uninstall()`, `plugin_status()`: report both hooks

### 2.5 doctor_cmd.py — Stop hook health check

**File:** `src/memoryschema/cli/doctor_cmd.py`

- After existing hook check (~line 270): add check for Stop hook registration

### 2.6 Tests

**File:** `tests/test_cli_hook.py`

- `test_install_creates_stop_entry`: verify `install` creates both PostToolUse and Stop entries
- `test_uninstall_removes_stop_entry`: verify `uninstall` removes both
- `test_status_shows_stop_hook`: verify `status` reports Stop hook state

### Verify Phase 2

```bash
pytest tests/test_cli_hook.py -v
# Manual Stop hook test:
mkdir -p /tmp/test-stop && echo "chain-test" > /tmp/test-stop/memory/.active_chain
cd /tmp/test-stop && bash /path/to/hook-stop.sh  # Should print reminder JSON
touch /tmp/claude-memory-chain-updated
cd /tmp/test-stop && bash /path/to/hook-stop.sh  # Should print {} and remove sentinel
rm -rf /tmp/test-stop
```

---

## Phase 3 — Documentation: Edit-not-Write guidance ✓ 371f708

### 3.1 docs/schema.md (source of truth)

**File:** `docs/schema.md`

- Line 516: after "the authorised chain accepts upserts" add: "Use the Edit tool (not Write) to update chain files — three targeted edits per response: append observation, replace description, replace reasoning. Write overwrites the entire `.md` file, risking observation loss."
- Line 520: "the hook fires on every write" → "the hook fires on every Write or Edit"
- Line 192 (enforcement): "on every Write to `memory/*.md`" → "on every Write or Edit to `memory/*.md`"

### 3.2 memory-working.tpl (template)

**File:** `src/memoryschema/templates/memory-working.tpl`

After line 46 ("File path" section), before line 49 ("Write decline"), add:

```markdown
## Chain updates

When updating a chain entity, use the **Edit** tool (not Write). Write replaces the 
entire file — if a previous observation is omitted, it is lost from the authoritative 
`.md` source. Edit preserves existing content and targets only the changed sections.
```

Note: the template has selective-write policy without chain lifecycle, so this is a standalone section, not embedded in lifecycle docs.

### 3.3 Plugin rules — memory-working.md

**File:** `.claude-plugin/rules/memory-working.md`

Lines 34-39 "How to update" section. Replace:

```
Write the SAME `memory/<chain-name>.md` file on every response. The upsert semantics handle accumulation (only works because the chain is authorised):
```

With:

```
**Edit** (not Write) the SAME `memory/<chain-name>.md` file on every response.
NEVER use Write on an existing chain file — it replaces the entire file, risking observation loss.

Three targeted Edits per update:
1. **Append** new `<memory:observation>` before `</memory:observations>`
2. **Replace** `<memory:description>` content
3. **Replace** `<memory:reasoning>` content

The upsert semantics at the index layer handle accumulation (only works because the chain is authorised):
```

### 3.4 Plugin rules — memory-schema.md

**File:** `.claude-plugin/rules/memory-schema.md`

- Line 192: "on every Write to `memory/*.md`" → "on every Write or Edit to `memory/*.md`"

### Verify Phase 3

- Read through each file for consistency
- Grep: `grep -rn '"Write"' docs/ .claude-plugin/rules/ src/memoryschema/templates/` — no stale bare `Write` references in hook/enforcement context

---

## Phase 4 — Deploy + cleanup ✓ deployed

### 4.1 Deploy to global settings

```bash
memoryschema plugin deploy --force
```

This updates:
- `~/.claude/rules/memory-working.md` (from `.claude-plugin/rules/`)
- `~/.claude/rules/memory-schema.md` (from `.claude-plugin/rules/`)
- `~/.claude/settings.json` — PostToolUse `Write|Edit` + Stop hook

### 4.2 Remove karpathy prototype

**File:** `/Volumes/RAID0/Users/shehzad/Projects/karpathy-llm-wiki/.claude/settings.local.json`

Delete or empty this file — the global hooks supersede it.

### Verify Phase 4

```bash
memoryschema hook status   # Shows Write|Edit + Stop hook
memoryschema doctor        # All checks pass
cat ~/.claude/rules/memory-working.md | grep -A5 "How to update"  # Shows Edit guidance
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/hooks/hook-post-write.sh` | Widen tool filter + sentinel touch | 1.1 |
| `src/memoryschema/hooks/hook-stop.sh` | **New** — Stop hook script | 2.1 |
| `.claude-plugin/hooks/hooks.json` | Widen matcher + Stop entry | 1.2, 2.2 |
| `src/memoryschema/cli/hook_cmd.py` | Matcher + Stop support | 1.3, 2.3 |
| `src/memoryschema/cli/plugin_cmd.py` | Matcher + Stop support | 1.4, 2.4 |
| `src/memoryschema/cli/doctor_cmd.py` | Matcher + Stop check | 1.5, 2.5 |
| `src/memoryschema/cli/main.py` | Init example (cosmetic) | 1.6 |
| `tests/test_cli_hook.py` | Matcher fixtures + Stop tests | 1.7, 2.6 |
| `docs/schema.md` | Edit guidance + "Write or Edit" | 3.1 |
| `src/memoryschema/templates/memory-working.tpl` | Chain updates section | 3.2 |
| `.claude-plugin/rules/memory-working.md` | Edit-not-Write in "How to update" | 3.3 |
| `.claude-plugin/rules/memory-schema.md` | "Write or Edit" in enforcement | 3.4 |
| `~/.claude/settings.json` | Via `plugin deploy --force` | 4.1 |
| `karpathy-llm-wiki/.claude/settings.local.json` | Remove prototype | 4.2 |

## Verification (end-to-end)

1. `pytest tests/ -x -q` — full suite green
2. Start chain: `memoryschema chain start chain-test`
3. Edit a memory file → sentinel touched → Stop hook returns `{}`
4. Don't edit any memory file → Stop hook returns reminder JSON
5. `memoryschema hook status` — both hooks registered
6. `memoryschema doctor` — all checks pass
7. `memoryschema plugin deploy --force` — deploys updated rules + hooks
