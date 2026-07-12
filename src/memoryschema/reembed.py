"""
Re-embedding utility.

Re-embeds store entries by prefix with full content.
Requires: pip install memory-schema[embeddings]

Usage:
    from memoryschema.reembed import reembed
    reembed(prefix='forum-', config=config, batch_size=20)
"""

import os
import sys
import time


from memoryschema.embedding_input import compose_embedding_text  # canonical source


def reembed(prefix, config=None, batch_size=20, max_chars=8000, dry_run=False,
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

    # Load through MemoryStore so sidecar vectors are REHYDRATED. A raw json.loads read of an
    # externalized store yields entries with NO inline vectors; the rewrite below would then
    # persist only the freshly computed vector and the sidecar rewrite would DESTROY every
    # other space vector for the whole corpus (found by the 2026-07-12 wide review).
    from memoryschema.store import MemoryStore
    _store = MemoryStore(store_path, config=config)
    entries = _store._load()

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
    _reembedded = set()

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
                    _reembedded.add(e.get('name'))
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

    # Re-stamp provenance for the re-embedded entries and force the sidecar to
    # rewrite (skip-if-unchanged would otherwise keep the OLD .npz when content —
    # hence embed_input_hash — is unchanged but the vector was recomputed).
    from memoryschema.embedding_input import embed_input_hash
    from memoryschema import vector_sidecar
    sdir = vector_sidecar.sidecar_dir(store_path)
    for entry in entries:
        if entry.get('name') in _reembedded:
            entry['embed_input_hash'] = embed_input_hash(entry)
            stale = vector_sidecar._npz_path(sdir, entry['name'])
            if os.path.exists(stale):
                try:
                    os.unlink(stale)
                except OSError:
                    pass

    # Write back through the store's own saver (atomic tmp+replace, externalizes to the
    # sidecar) — the entries are fully rehydrated, so every space vector survives the rewrite.
    _store._save(entries)

    # Recompute associations
    if not skip_assoc and embedded > 0:
        stats['associations'] = _store.compute_associations(k=10)

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

    from memoryschema.spaces import apply_full_embeddings
    from memoryschema import vector_sidecar

    entries = store.list_all(include_inactive=True)
    matched = [e for e in entries if e.get('name', '').startswith(prefix)]
    stats = {'matched': len(matched), 'embedded': 0, 'skipped_empty': 0}
    if dry_run:
        stats['dry_run'] = True
        return stats

    # Sidecar + mirror plumbing: content is unchanged on a backfill, so externalize's
    # skip-if-unchanged (same embed_input_hash) would DROP the freshly computed vectors —
    # unlink each entity's .npz first to force the rewrite (same defense as reembed()).
    # And when the active store is Neo4j, ALSO mirror to the JSONL store (index_memory's
    # dual-write pattern): otherwise the next reconcile pushes the stale JSONL vectors
    # back over the fresh Neo4j ones (reconcile rebuilds Neo4j FROM the JSONL).
    jsonl_path = str(config.store_path)
    sdir = vector_sidecar.sidecar_dir(jsonl_path)
    jsonl_mirror = None
    if type(store).__name__ != 'MemoryStore':
        from memoryschema.store import MemoryStore
        jsonl_mirror = MemoryStore(jsonl_path, config=config)

    for entry in matched:
        if not apply_full_embeddings(entry, config=config):    # shared derived-layer write
            stats['skipped_empty'] += 1
            continue
        name = entry.get('name') or ''
        stale = vector_sidecar._npz_path(sdir, name)
        if name and os.path.exists(stale):
            try:
                os.unlink(stale)
            except OSError:
                pass
        store.upsert(entry)
        if jsonl_mirror is not None:
            try:
                jsonl_mirror.upsert(entry)
            except Exception as ex:
                print(f'WARN jsonl mirror failed for {name}: {ex}', file=sys.stderr)
        stats['embedded'] += 1

    return stats
