#!/bin/bash
# PostToolUse hook for memory file indexing.
#
# Triggered by Claude Code after every Write or Edit tool call.
# NOTE: Despite the filename, this hook handles both Write and Edit calls.
# The name is preserved for backward compatibility.
# Uses the memoryschema package (pip install memory-schema).
# One hook handles ALL projects — derives project root from file path.
#
# Output format (PostToolUse event):
#   PostToolUse hooks support hookSpecificOutput with additionalContext.
#   This hook returns no stdout JSON (pass-through via exit code only).
#   See docs/harness-manual.md §9.4 (hook output formats).
#
# Exit codes:
#   0 — success (or non-memory write, silently ignored)
#   2 — flag for Claude review (indexing error)

set -uo pipefail

# Self-sufficiency: force UTF-8 for every python child. Claude Code's hook environment does not
# set it, and on Windows the default cp1252 codec crashes lazy reads of UTF-8 store/entity files
# (UnicodeDecodeError on bytes like 0x8f — observed live in a consumer 2026-07-14). Belt for the
# whole inline pipeline; the individual open() calls below carry encoding='utf-8' as suspenders.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Resolve Python: argument > env var > auto-detect > bare python3
if [ -n "${1:-}" ] && [ -x "${1:-}" ]; then
    PYTHON="$1"
elif [ -n "${MEMORYSCHEMA_PYTHON:-}" ]; then
    PYTHON="$MEMORYSCHEMA_PYTHON"
else
    PYTHON=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && \
           "$candidate" -c "import memoryschema" >/dev/null 2>&1; then
            PYTHON="$candidate"
            break
        fi
    done
    if [ -z "$PYTHON" ]; then
        echo "hook: cannot find Python with memoryschema installed" >&2
        exit 0  # Don't block writes
    fi
fi

# Read JSON from stdin
INPUT=$(cat)

# Extract tool name and file path
TOOL_NAME=$(echo "$INPUT" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)

# Only process Write and Edit tool calls
if [ "$TOOL_NAME" != "Write" ] && [ "$TOOL_NAME" != "Edit" ]; then
    exit 0
fi

FILE_PATH=$(echo "$INPUT" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Normalize Windows backslashes to forward slashes so path matching is reliable
FILE_PATH="${FILE_PATH//\\//}"

# Only process memory files (path contains /memory/ and ends with .md)
if [[ "$FILE_PATH" != *"/memory/"* ]] || [[ "$FILE_PATH" != *.md ]]; then
    exit 0
fi

# Self-sufficiency: load the project's .env (the path component before /memory/)
# so the hook has DB/API credentials even though Claude Code's hook environment
# does not export them. Comment/blank lines skipped; values are not eval'd.
ENV_FILE="${FILE_PATH%%/memory/*}/.env"
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r _line || [ -n "$_line" ]; do
        case "$_line" in
            ''|'#'*) continue ;;
        esac
        _line="${_line#export }"
        case "$_line" in
            *=*)
                _key="${_line%%=*}"
                _val="${_line#*=}"
                _key="${_key//[[:space:]]/}"
                # Quote FIRST, then comment: a quoted value is taken verbatim (dotenv
                # convention; matches the CLI parser — a quoted NEO4J_PASSWORD="x" must
                # export x). Stripping the inline comment first would truncate a quoted
                # value that legitimately contains ' #' and leave an unbalanced quote.
                case "$_val" in
                    '"'*'"') _val="${_val#\"}"; _val="${_val%\"}" ;;
                    "'"*"'") _val="${_val#\'}"; _val="${_val%\'}" ;;
                    *) _val="${_val%%[[:space:]]#*}" ;;   # unquoted: strip ' # comment', keep '#' in-word
                esac
                # SECURITY: export ONLY the keys the indexer needs. The .env may hold unrelated secrets
                # (cloud tokens, other services); leaking the whole file into every hook child process is
                # needless exposure. Allowlist the memory backend's own namespaces.
                case "$_key" in
                    NEO4J_*|VOYAGE_*|MEMORYSCHEMA_*|MEMORY_PROJECT|MEMORY_GENERATOR|MEMORY_ROOT)
                        [ -n "$_key" ] && export "$_key=$_val" ;;
                    *) : ;;   # ignore keys outside the memory backend's namespace
                esac
                ;;
        esac
    done < "$ENV_FILE"
fi

# Touch sentinel so the Stop hook knows a memory file was updated this response.
# Project-relative (not /tmp): the CLI write path and the Stop hook must agree on the
# path, and POSIX /tmp differs from native-Windows-Python's /tmp (see write_index.py).
_SENTINEL_DIR="${FILE_PATH%%/memory/*}/.memoryschema"
mkdir -p "$_SENTINEL_DIR" 2>/dev/null || true
touch "$_SENTINEL_DIR/chain-updated" 2>/dev/null || true

# Skip MEMORY.md index file
if [[ "$(basename "$FILE_PATH")" == "MEMORY.md" ]]; then
    exit 0
fi

# Run the canonical indexing pipeline: write_index.index_memory — the SAME code path the CLI
# (remember / chain step / write) uses. The hook is a thin exit-code shim over it; the previous
# ~200-line inline duplicate pipeline drifted behind index_memory three separate times (quarantine
# parity, config threading, the cp1252 store scan) — v0.2.0 unification removes the class.
# One behavior improvement rides along: index_memory DUAL-writes (Neo4j AND JSONL), so hook writes
# no longer leave store.jsonl lagging Neo4j until the next reconcile.
# Pass the file path via the ENVIRONMENT, never interpolated into the source: a
# path containing a single quote (e.g. C:/Users/O'Brien/...) would otherwise break
# the Python literal (every write fails) or inject arbitrary code.
MEMORYSCHEMA_HOOK_FILE="$FILE_PATH" "$PYTHON" -c "
import os, sys

filepath = os.environ['MEMORYSCHEMA_HOOK_FILE']
try:
    from memoryschema.write_index import index_memory
except ImportError:
    sys.exit(0)   # package not importable in this interpreter — never block writes

res = index_memory(filepath)
for w in res.warnings:
    print('hook: %s' % w, file=sys.stderr)

if res.ok or getattr(res, 'skipped', False):
    sys.exit(0)                       # indexed, or not a memory entity (notes/README) — quiet
if getattr(res, 'blocked', False):
    # read-only auth veto: report it but exit 0 — never block the Write tool itself
    print('hook: %s' % '; '.join(str(e) for e in res.errors), file=sys.stderr)
    sys.exit(0)
# corruption / gate REJECT / both-stores-failed: LOUD — exit 2 feeds stderr straight back to
# the agent in the same turn so it can fix the file or escalate
print('hook: %s [file: %s]' % ('; '.join(str(e) for e in res.errors), filepath), file=sys.stderr)
sys.exit(2)
"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "hook: memory indexing failed for $FILE_PATH" >&2
    exit 2
fi

exit 0
