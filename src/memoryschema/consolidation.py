"""
Batch memory consolidation.

Batch processes un-indexed memory files: discover -> parse -> upsert
-> compute backlinks -> optionally embed + compute associations.
"""

import sys

from memoryschema.tags import parse_memory_file
from memoryschema.discovery import discover_memory_files
from memoryschema.store import MemoryStore


def _embedding_text(memory):
    """Compose the text to embed for a memory.

    Uses description + observations + prompt + reasoning.
    """
    parts = [memory.get('description', '')]
    parts.extend(memory.get('observations', []))
    if memory.get('prompt'):
        parts.append(memory['prompt'])
    if memory.get('reasoning'):
        parts.append(memory['reasoning'])
    return ' '.join(parts)


def consolidate(base_path, project, store, embed=False):
    """Discover and index all memory files under base_path.

    Parses each file via tags.py, upserts into the store,
    recomputes backlinks, and optionally embeds via Voyage.

    Args:
        base_path: Root directory containing memory .md files.
        project: Project name for scoping.
        store: MemoryStore or Neo4jMemoryStore instance.
        embed: If True, embed each memory via Voyage and compute associations.

    Returns:
        Dict with counts: {synced, skipped, backlinks, embedded, associations}.
    """
    filepaths = discover_memory_files(base_path)
    synced = 0
    skipped = 0
    embedded = 0

    embed_fn = None
    if embed:
        try:
            from memoryschema.embeddings import embed_text
            embed_fn = embed_text
        except (ImportError, Exception):
            print('Warning: embeddings unavailable, skipping embedding', file=sys.stderr)

    for filepath in filepaths:
        memory = parse_memory_file(filepath)
        if memory is None:
            skipped += 1
            continue
        if memory.get('project') is None:
            memory['project'] = project

        if embed_fn:
            existing = store.get(memory.get('name'))
            if not existing or not existing.get('embedding'):
                try:
                    text = _embedding_text(memory)
                    memory['embedding'] = embed_fn(text)
                    embedded += 1
                except Exception:
                    pass

        store.upsert(memory)
        synced += 1

    backlinks = store.compute_backlinks() if synced > 0 else 0
    associations = 0
    if embedded > 0:
        associations = store.compute_associations()

    return {
        'synced': synced,
        'skipped': skipped,
        'backlinks': backlinks,
        'embedded': embedded,
        'associations': associations,
    }
