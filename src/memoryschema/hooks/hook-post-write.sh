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
#   See docs/technical-reference.md § Hook Output Formats.
#
# Exit codes:
#   0 — success (or non-memory write, silently ignored)
#   2 — flag for Claude review (indexing error)

set -uo pipefail

# Use the Python where memoryschema is installed
PYTHON="${MEMORYSCHEMA_PYTHON:-/Volumes/RAID0/Users/shehzad/.pyenv/versions/3.12.3/bin/python3}"

# Read JSON from stdin
INPUT=$(cat)

# Extract tool name and file path
TOOL_NAME=$(echo "$INPUT" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)

# Only process Write and Edit tool calls
if [ "$TOOL_NAME" != "Write" ] && [ "$TOOL_NAME" != "Edit" ]; then
    exit 0
fi

FILE_PATH=$(echo "$INPUT" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Only process memory files (path contains /memory/ and ends with .md)
if [[ "$FILE_PATH" != *"/memory/"* ]] || [[ "$FILE_PATH" != *.md ]]; then
    exit 0
fi

# Touch sentinel so Stop hook knows a memory file was updated this response
touch /tmp/claude-memory-chain-updated 2>/dev/null || true

# Skip MEMORY.md index file
if [[ "$(basename "$FILE_PATH")" == "MEMORY.md" ]]; then
    exit 0
fi

# Run the Python indexing pipeline using memoryschema package
"$PYTHON" -c "
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
        from memoryschema.embeddings import embed_text
        from memoryschema.embedding_input import compose_embedding_text
        # Default space (all fields blended)
        text = compose_embedding_text(memory, space='default')
        default_vec = embed_text(text, config=hook_config)
        memory['embedding'] = default_vec
        memory['embeddings'] = {'default': default_vec}
        # Field spaces: 1:1 mapping per field (skip if empty)
        for space in ('name', 'description', 'observations', 'prompt', 'reasoning', 'chain'):
            field_text = compose_embedding_text(memory, space=space)
            if field_text:
                memory['embeddings'][space] = embed_text(field_text, config=hook_config)
        # Compute divergence profile: cosine distance of each field space from default
        div_profile = {}
        for space, vec in memory['embeddings'].items():
            if space != 'default' and vec and default_vec:
                dot = sum(a * b for a, b in zip(default_vec, vec))
                na = sum(a * a for a in default_vec) ** 0.5
                nb = sum(b * b for b in vec) ** 0.5
                sim = dot / (na * nb) if na > 0 and nb > 0 else 0.0
                div_profile[space] = round(1.0 - sim, 4)
        if div_profile:
            memory['divergence_profile'] = div_profile
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

# Update MEMORY.md
name = memory.get('name', '')
if name:
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
        # Enforce L0 token budget (evict lowest-scoring entries)
        try:
            from memoryschema.l0_budget import enforce_budget
            result = enforce_budget(index_path, store_path)
            if result['evicted']:
                print(f'hook: L0 evicted {len(result[\"evicted\"])} entries '
                      f'({result[\"tokens_before\"]}→{result[\"tokens_after\"]} tokens)',
                      file=sys.stderr)
        except Exception:
            pass  # Budget enforcement failure does not block
        # Progressive disclosure: group entries by type
        try:
            from memoryschema.l0_budget import categorize_index
            categorize_index(index_path, store_path)
        except Exception:
            pass  # Categorization failure does not block
    except Exception:
        pass  # MEMORY.md update failure does not block indexing
"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "hook: memory indexing failed for $FILE_PATH" >&2
    exit 2
fi

exit 0
