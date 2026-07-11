#!/bin/bash
# Stop hook: reminds Claude to update the active chain if no memory write
# happened this response. Works with hook-post-write.sh which touches the
# sentinel on every memory file write.
#
# Output format (Stop event):
#   Stop hooks do NOT support hookSpecificOutput. Use top-level fields only.
#   Valid:   {"systemMessage": "..."}
#   Invalid: {"hookSpecificOutput": {"additionalContext": "..."}}
#   See docs/harness-manual.md §9.4 (hook output formats).
#
# Exit codes:
#   0 — always (Stop hooks must not block)

set -uo pipefail

CHAIN_FILE="memory/.active_chain"
# Project-relative (cwd = project root, as for CHAIN_FILE): the CLI write path and the
# PostToolUse hook write this same path. /tmp is unreliable — native-Windows-Python's
# /tmp (C:\tmp) differs from Git Bash's, which made CLI chain-steps miss the sentinel
# and fire a false "chain NOT updated" reminder every turn.
SENTINEL=".memoryschema/chain-updated"

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

# Chain active but not updated — inject reminder (Stop hooks use systemMessage, not hookSpecificOutput)
echo "{\"systemMessage\":\"MEMORY CHAIN REMINDER: The active chain \\\"$CHAIN_NAME\\\" was NOT updated this response. Edit memory/$CHAIN_NAME.md now (use Edit, not Write).\"}"
exit 0
