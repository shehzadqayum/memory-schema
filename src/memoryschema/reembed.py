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


def reembed(prefix, config=None, batch_size=20, max_chars=2000, dry_run=False, skip_assoc=False):
    """Re-embed entries matching prefix.

    Args:
        prefix: Name prefix filter (e.g., 'forum-', 'tweet-').
        config: MemoryConfig instance. Uses defaults if None.
        batch_size: Embedding batch size.
        max_chars: Max chars per embedding text.
        dry_run: Show stats without re-embedding.
        skip_assoc: Skip association recomputation.

    Returns:
        Dict with stats: {total, matched, embedded, associations}.
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
        'associations': 0,
    }

    if not target_entries or dry_run:
        stats['dry_run'] = dry_run
        return stats

    from memoryschema.embeddings import embed_batch as _embed_batch

    embedded = 0
    total = len(target_entries)
    total_batches = (total + batch_size - 1) // batch_size

    for i in range(0, total, batch_size):
        batch = target_entries[i:i + batch_size]
        texts = [compose_embedding_text(e, max_chars=max_chars) for e in batch]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                vectors = _embed_batch(texts, config=config)
                for e, vec in zip(batch, vectors):
                    e['embedding'] = vec
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
