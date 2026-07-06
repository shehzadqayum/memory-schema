#!/bin/bash
# Stop hook: reminds Claude to update the active chain if no memory write
# happened this response. Works with hook-post-write.sh which touches the
# sentinel on every memory file write.
#
# Output format (Stop event):
#   Stop hooks do NOT support hookSpecificOutput. Use top-level fields only.
#   Valid:   {"systemMessage": "..."}
#   Invalid: {"hookSpecificOutput": {"additionalContext": "..."}}
#   See docs/memory-system-specification.md §9.4 (hook output formats).
#
# Exit codes:
#   0 — always (Stop hooks must not block)

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

# Chain active but not updated — inject reminder (Stop hooks use systemMessage, not hookSpecificOutput)
echo "{\"systemMessage\":\"MEMORY CHAIN REMINDER: The active chain \\\"$CHAIN_NAME\\\" was NOT updated this response. Edit memory/$CHAIN_NAME.md now (use Edit, not Write).\"}"
exit 0
