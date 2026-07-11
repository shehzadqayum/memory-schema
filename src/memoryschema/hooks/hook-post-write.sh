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
                [ -n "$_key" ] && export "$_key=$_val"
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

# Run the Python indexing pipeline using memoryschema package.
# Pass the file path via the ENVIRONMENT, never interpolated into the source: a
# path containing a single quote (e.g. C:/Users/O'Brien/...) would otherwise break
# the Python literal (every write fails) or inject arbitrary code.
MEMORYSCHEMA_HOOK_FILE="$FILE_PATH" "$PYTHON" -c "
import sys, os

# Derive project root from file path (parent of memory/)
filepath = os.environ['MEMORYSCHEMA_HOOK_FILE']
parts = filepath.replace('\\\\', '/').split('/')
project_root = None
for i, part in enumerate(parts):
    if part == 'memory' and i > 0:
        project_root = '/'.join(parts[:i])
        break
if project_root is None:
    # Hybrid scope fallback: use user-level memory directory
    project_root = os.path.expanduser('~/.claude')

# Ensure memory directory exists (user-level fallback may not have it yet)
memory_dir_path = os.path.join(project_root, 'memory')
os.makedirs(memory_dir_path, exist_ok=True)

# Derive store path
store_path = os.path.join(project_root, 'memory', 'store.jsonl')

from memoryschema.tags import parse_memory_file

memory = parse_memory_file(filepath)
if memory is None:
    # Distinguish CORRUPTION (an entity file that fails to parse — e.g. an unescaped '<' or '&'
    # in prose, the M14 class that silently truncated the store twice) from a genuine
    # not-a-memory-entity file. validator.validate already separates the two: V1 = no entity
    # element (skip quietly), V9 = XML parse error with ElementTree's line/column (fail LOUD:
    # exit 2 feeds stderr straight back to the agent in the same turn so it can fix the escape).
    try:
        from memoryschema.validator import validate as _validate
        with open(filepath, 'r', encoding='utf-8') as _f:
            _content = _f.read()
        _errs = _validate(_content, filepath=filepath)   # returns a list of (rule_id, message) tuples
        _parse_errs = [e for e in _errs if str(e[0] if isinstance(e, (list, tuple)) else e).startswith('V9')
                       or 'parse error' in str(e).lower() or 'Unclosed' in str(e)]
        if _parse_errs:
            print('memoryschema hook: MEMORY FILE CORRUPTED — XML parse failed and the entity was '
                  'NOT indexed (store keeps the stale version). Fix the file (likely an unescaped '
                  '< or & in prose; XML-escape as &lt; &amp;). Details: '
                  + '; '.join(str(e) for e in _parse_errs[:3]) + ' [file: ' + filepath + ']',
                  file=sys.stderr)
            sys.exit(2)
    except SystemExit:
        raise
    except Exception:
        pass  # never let the corruption-check itself break the hook
    # Not a memory entity file (e.g., YAML frontmatter, plain markdown) — skip
    sys.exit(0)

# Authorisation check: only the active chain or new memories can be written
# Active chain name stored in memory/.active_chain
name = memory.get('name', '')
active_chain_path = os.path.join(project_root, 'memory', '.active_chain')
active_chain = None
if os.path.exists(active_chain_path):
    with open(active_chain_path, 'r') as f:
        active_chain = f.read().strip()

# Check if this name already exists in the store
existing = None
if os.path.exists(store_path):
    import json as _json
    with open(store_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = _json.loads(line)
                if entry.get('name') == name:
                    existing = entry
                    break
            except _json.JSONDecodeError:
                continue

if existing is not None:
    # Entity exists — only allow upsert if this is the active chain
    if name != active_chain:
        print(f'hook: BLOCKED — {name} is read-only (not the active chain)', file=sys.stderr)
        sys.exit(0)  # exit 0 = don't block the Write tool, just skip indexing

# Generator stamp (v4): read MEMORY_GENERATOR env var
generator_id = os.environ.get('MEMORY_GENERATOR')
if generator_id:
    memory['generator'] = generator_id

# Construct store + config BEFORE embed (embed needs config for API key)
hook_store = None
hook_config = None
try:
    from memoryschema.config import MemoryConfig
    hook_config = MemoryConfig(project_root=project_root)
except Exception:
    pass
try:
    from memoryschema.store import MemoryStore
    hook_store = MemoryStore(store_path)
except Exception:
    pass

# Embed BEFORE gate (stages 4-6 need the embedding vector)
# Check both env var and config for API key (subprocess may not inherit env)
voyage_key = os.environ.get('VOYAGE_API_KEY') or (
    hook_config.voyage_api_key if hook_config else None)
if voyage_key:
    try:
        # Canonical multi-space embed + divergence (shared with the backfill so the
        # two cannot drift). Computes the 'default' blend + each non-empty field space
        # and the divergence profile (1 - cosine to default).
        from memoryschema.spaces import embed_all_spaces
        from memoryschema.embedding_input import embed_input_hash
        embeddings, div_profile = embed_all_spaces(memory, config=hook_config)
        if embeddings:
            memory['embedding'] = embeddings.get('default')
            memory['embeddings'] = embeddings
            if div_profile:
                memory['divergence_profile'] = div_profile
            memory['embed_input_hash'] = embed_input_hash(memory)
    except Exception:
        pass  # Embedding failure does not block — stages 4-6 skip gracefully

# Write gate: full pipeline with store + config (stages 1-6)
try:
    from memoryschema.write_gate import gate_pipeline, GateVerdict
    gate_result = gate_pipeline(memory, store=hook_store, config=hook_config)
    for w in gate_result.warnings:
        print(f'hook: gate: {w}', file=sys.stderr)
    for r in gate_result.reasons:
        print(f'hook: gate: {r}', file=sys.stderr)
    if gate_result.verdict == GateVerdict.REJECT:
        print(f'hook: write gate REJECTED {filepath}', file=sys.stderr)
        sys.exit(2)
    if gate_result.verdict == GateVerdict.QUARANTINE:
        print(f'hook: write gate QUARANTINED {filepath}', file=sys.stderr)
        memory['status'] = 'quarantined'
        # Fall through to upsert — quarantined entries are saved unembedded
        memory.pop('embedding', None)
        memory.pop('embeddings', None)
        memory.pop('divergence_profile', None)
except ImportError:
    pass  # write_gate not available — skip validation

# Try Neo4j first (O(1) upsert, <10ms)
indexed = False
try:
    from memoryschema.neo4j_store import Neo4jMemoryStore
    store = Neo4jMemoryStore()
    store.upsert(memory)
    if memory.get('embedding'):
        store.compute_associations_single(memory['name'])
    indexed = True
except Exception:
    pass  # Fall through to JSONL

# Fallback: JSONL
if not indexed:
    try:
        from memoryschema.store import MemoryStore
        store = MemoryStore(store_path)
        store.upsert(memory)
        store.compute_backlinks()
        if memory.get('embedding'):
            store.compute_associations()
        indexed = True
    except Exception as e:
        print(f'hook: both stores failed for {filepath}: {e}', file=sys.stderr)

if not indexed:
    sys.exit(2)

# Rebuild MEMORY.md (L0) as a faithful, status-filtered index of the store's ACTIVE set.
# A full REGENERATE — not an append — so superseded/archived entries drop out and any
# previously-evicted active entries come back (fixes the drift where the append-only index
# lingered stale entries and lost active ones). Read from the SAME store just written to
# (Neo4j when up, JSONL otherwise) so the just-written memory is included even though
# store.jsonl can lag Neo4j between reconciles.
name = memory.get('name', '')
if name:
    try:
        index_path = os.path.join(os.path.dirname(filepath), 'MEMORY.md')
        budget = getattr(hook_config, 'l0_token_budget', 2000) if hook_config else 2000
        active = store.list_all(include_inactive=False)
        from memoryschema.l0_budget import rebuild_index
        rebuild_index(index_path, entries=active, token_budget=budget)
    except Exception:
        pass  # MEMORY.md update failure does not block indexing
"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "hook: memory indexing failed for $FILE_PATH" >&2
    exit 2
fi

exit 0
