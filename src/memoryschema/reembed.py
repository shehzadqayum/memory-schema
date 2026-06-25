"""
Re-embedding utility.

Re-embeds store entries by prefix with full content.
Requires: pip install memory-schema[embeddings]

Usage:
    from memoryschema.reembed import reembed
    reembed(prefix='forum-', config=config, batch_size=20)
"""

import json
import os
import sys
import tempfile
import time


from memoryschema.embedding_input import compose_embedding_text  # canonical source


def reembed(prefix, config=None, batch_size=20, max_chars=2000, dry_run=False,
            skip_assoc=False, space=None):
    """Re-embed entries matching prefix.

    Args:
        prefix: Name prefix filter (e.g., 'forum-', 'tweet-').
        config: MemoryConfig instance. Uses defaults if None.
        batch_size: Embedding batch size.
        max_chars: Max chars per embedding text.
        dry_run: Show stats without re-embedding.
        skip_assoc: Skip association recomputation.
        space: Embedding space to target (e.g., 'observations', 'reasoning').
            If None, embeds in the default space (backward compat).
            Entries with empty text for the target space are skipped
            (structural absence — no observations or no reasoning).

    Returns:
        Dict with stats: {total, matched, embedded, skipped_empty, associations}.
    """
    if config is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()

    store_path = str(config.store_path)

    with open(store_path, 'r', encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]

    target_entries = [e for e in entries if e.get('name', '').startswith(prefix)]

    stats = {
        'total': len(entries),
        'matched': len(target_entries),
        'embedded': 0,
        'skipped_empty': 0,
        'associations': 0,
    }
    if space:
        stats['space'] = space

    if not target_entries or dry_run:
        stats['dry_run'] = dry_run
        return stats

    # For field spaces, filter out entries with empty text (structural absence)
    embed_space = space or 'default'
    embeddable = []
    for e in target_entries:
        text = compose_embedding_text(e, space=embed_space, max_chars=max_chars)
        if text:
            embeddable.append((e, text))
        else:
            stats['skipped_empty'] += 1

    if not embeddable:
        return stats

    from memoryschema.embeddings import embed_batch as _embed_batch

    embedded = 0

    for i in range(0, len(embeddable), batch_size):
        batch = embeddable[i:i + batch_size]
        texts = [text for _, text in batch]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                vectors = _embed_batch(texts, config=config)
                for (e, _), vec in zip(batch, vectors):
                    if space:
                        e.setdefault('embeddings', {})[space] = vec
                    else:
                        e['embedding'] = vec
                        e.setdefault('embeddings', {})['default'] = vec
                embedded += len(batch)
                break
            except Exception as ex:
                if attempt < max_retries - 1:
                    delay = 2.0 * (2 ** attempt)
                    time.sleep(delay)
                else:
                    print(f'FAIL batch {i // batch_size + 1}: {ex}', file=sys.stderr)

        time.sleep(0.3)

    stats['embedded'] = embedded

    # Write store back atomically
    dirpath = os.path.dirname(store_path)
    fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=dirpath)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        os.replace(tmp_path, store_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # Recompute associations
    if not skip_assoc and embedded > 0:
        from memoryschema.store import MemoryStore
        store = MemoryStore(store_path)
        stats['associations'] = store.compute_associations(k=10)

    return stats


def reembed_all_spaces(prefix='', config=None, store=None, dry_run=False):
    """Backfill full multi-space embeddings + divergence into the configured store.

    For each entry whose name starts with `prefix`, compute every embedding space
    (spaces.embed_all_spaces) + its divergence profile, set
    embedding/embeddings/divergence_profile, and upsert through the active store
    backend (Neo4j when available, else JSONL) — so both backends gain the
    multi-space data, unlike `reembed` which only rewrites the JSONL file.

    store.upsert bypasses the hook's active-chain write gate (that gate lives only
    in the hook), so read-only entries are safely backfilled.

    Returns stats: {matched, embedded, skipped_empty}.
    """
    if config is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()
    if store is None:
        from memoryschema.store import get_store
        store = get_store(config=config)

    from memoryschema.spaces import embed_all_spaces

    entries = store.list_all(include_inactive=True)
    matched = [e for e in entries if e.get('name', '').startswith(prefix)]
    stats = {'matched': len(matched), 'embedded': 0, 'skipped_empty': 0}
    if dry_run:
        stats['dry_run'] = True
        return stats

    for entry in matched:
        embeddings, divergence = embed_all_spaces(entry, config=config)
        if not embeddings:
            stats['skipped_empty'] += 1
            continue
        entry['embedding'] = embeddings.get('default')
        entry['embeddings'] = embeddings
        if divergence:
            entry['divergence_profile'] = divergence
        store.upsert(entry)
        stats['embedded'] += 1

    return stats
