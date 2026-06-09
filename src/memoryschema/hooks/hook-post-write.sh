#!/bin/bash
# PostToolUse hook for memory file indexing.
#
# Triggered by Claude Code after every Write tool call.
# Uses the memoryschema package (pip install memory-schema).
# One hook handles ALL projects — derives project root from file path.
#
# Exit codes:
#   0 — success (or non-memory write, silently ignored)
#   2 — flag for Claude review (indexing error)

set -uo pipefail

# Read JSON from stdin
INPUT=$(cat)

# Extract tool name and file path
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)

# Only process Write tool calls
if [ "$TOOL_NAME" != "Write" ]; then
    exit 0
fi

FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Only process memory files (path contains /memory/ and ends with .md)
if [[ "$FILE_PATH" != *"/memory/"* ]] || [[ "$FILE_PATH" != *.md ]]; then
    exit 0
fi

# Skip MEMORY.md index file
if [[ "$(basename "$FILE_PATH")" == "MEMORY.md" ]]; then
    exit 0
fi

# Run the Python indexing pipeline using memoryschema package
python3 -c "
import sys, os

# Derive project root from file path (parent of memory/)
filepath = '$FILE_PATH'
parts = filepath.replace('\\\\', '/').split('/')
project_root = None
for i, part in enumerate(parts):
    if part == 'memory' and i > 0:
        project_root = '/'.join(parts[:i])
        break
if project_root is None:
    project_root = os.path.dirname(filepath)

# Derive store path
store_path = os.path.join(project_root, 'memory', 'store.jsonl')

from memoryschema.tags import parse_memory_file

memory = parse_memory_file(filepath)
if memory is None:
    print(f'hook: failed to parse {filepath}', file=sys.stderr)
    sys.exit(2)

# Embed if VOYAGE_API_KEY is set (optional, graceful degradation)
if os.environ.get('VOYAGE_API_KEY'):
    try:
        from memoryschema.embeddings import embed_text
        parts = [memory.get('description', ''), ' '.join(memory.get('observations', []))]
        if memory.get('prompt'):
            parts.append(memory['prompt'])
        if memory.get('reasoning'):
            parts.append(memory['reasoning'])
        text = ' '.join(parts)
        memory['embedding'] = embed_text(text.strip())
    except Exception:
        pass  # Embedding failure does not block indexing

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

# Update MEMORY.md for compact resilience (working memory only)
name = memory.get('name', '')
if name and not name.startswith('tweet-') and not name.startswith('forum-'):
    try:
        memory_dir = os.path.dirname(filepath)
        index_path = os.path.join(memory_dir, 'MEMORY.md')
        desc = memory.get('description', name)
        filename = os.path.basename(filepath)
        entry = f'- [{name}]({filename}) — {desc}'
        existing = ''
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                existing = f.read()
        if f'[{name}]' not in existing:
            existing = existing.rstrip('\n') + '\n' + entry + '\n'
            with open(index_path, 'w') as f:
                f.write(existing)
    except Exception:
        pass  # MEMORY.md update failure does not block indexing
"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "hook: memory indexing failed for $FILE_PATH" >&2
    exit 2
fi

exit 0
