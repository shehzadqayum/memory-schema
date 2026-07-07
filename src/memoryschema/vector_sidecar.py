"""Vector sidecar: embeddings live in per-entity .npz files, not in store.jsonl.

Measured motivation (plan-memory-system-improvement Phase 2d): store.jsonl was
8.41 MB for 55 entities — 91.5% of it embedding-vector JSON — and EVERY mutation
(upsert, access-count bump) rewrites the whole file (~0.8s). Externalizing the
vectors shrinks the rewrite to ~0.7 MB, makes store.jsonl git-diffable, and makes
loads faster (binary float32 beats parsing millions of JSON float literals).

Design: transparent at the store boundary — externalize on SAVE, rehydrate on
LOAD — so no consumer (scoring, recall, associations) changes. Entries carry
"vectors_external": true in the file; in memory they look exactly as before.

The sidecar is DERIVED data (rebuildable from Neo4j or by re-embedding), so
memory/.embeddings/ is gitignored. Skip-if-unchanged uses embed_input_hash: the
.npz is rewritten only when the provenance hash differs.

Degrades gracefully: without numpy (voyageai absent), vectors stay inline —
exactly the pre-sidecar behavior.
"""

import os

VEC_KEYS = ("embedding", "embeddings")
MARKER = "vectors_external"


def _np():
    try:
        import numpy
        return numpy
    except ImportError:
        return None


def sidecar_dir(store_path):
    """memory/.embeddings next to the store file."""
    return os.path.join(os.path.dirname(os.path.abspath(str(store_path))), ".embeddings")


def _npz_path(sdir, name):
    return os.path.join(sdir, "%s.npz" % name)


def _unsafe_name(name):
    """True if `name` cannot be a plain file inside the sidecar dir.

    An entity name is used raw as the .npz filename; a name containing a path
    separator or '..' would write OUTSIDE memory/.embeddings (traversal), and a
    Windows-illegal character would make open() raise mid-_save, failing every
    subsequent store write for the whole corpus. Names are not hard-validated to
    kebab at creation, so guard here: unsafe names keep their vectors inline
    rather than escape the dir or crash the save.
    """
    if not name or name in (".", ".."):
        return True
    if name != os.path.basename(name):        # contains a separator
        return True
    return any(c in name for c in '\\/:*?"<>|')


def externalize(entry, sdir):
    """Return a shallow copy of `entry` with vectors moved to <name>.npz.

    Writes the .npz only when missing or the stored provenance hash differs
    (embeddings are immutable per content-version). If numpy is unavailable, the
    entry has no vectors/name, or the name is not a safe filename, returns the
    entry unchanged (inline).
    """
    np = _np()
    name = entry.get("name")
    has_vec = any(entry.get(k) for k in VEC_KEYS)
    if np is None or not name or not has_vec or _unsafe_name(name):
        return entry

    os.makedirs(sdir, exist_ok=True)
    path = _npz_path(sdir, name)
    cur_hash = entry.get("embed_input_hash") or ""

    write_needed = True
    if os.path.exists(path) and cur_hash:
        try:
            with np.load(path, allow_pickle=False) as z:
                stored = str(z["hash"]) if "hash" in z.files else ""
            write_needed = stored != cur_hash
        except Exception:
            write_needed = True

    if write_needed:
        arrays = {"hash": np.array(cur_hash)}
        if entry.get("embedding"):
            arrays["embedding"] = np.asarray(entry["embedding"], dtype=np.float32)
        for space, vec in (entry.get("embeddings") or {}).items():
            if vec:
                arrays["sp_" + space] = np.asarray(vec, dtype=np.float32)
        tmp = path + ".tmp.npz"
        try:
            with open(tmp, "wb") as f:
                np.savez_compressed(f, **arrays)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    out = dict(entry)
    for k in VEC_KEYS:
        out.pop(k, None)
    out[MARKER] = True
    return out


def rehydrate(entry, sdir):
    """Load vectors back into an entry saved with externalize (in place).

    The marker is popped ONLY on a successful rehydrate. If we cannot rehydrate
    now (no numpy, missing/corrupt .npz), the marker is KEPT — otherwise the next
    store._save would persist the entry with neither vectors nor marker,
    permanently detaching an intact sidecar (e.g. a single mutation run from a
    numpy-less Python would silently strip the whole corpus's embeddings). The
    entry is treated as unembedded for THIS load; a later load (or reconcile)
    retries via the still-present marker.
    """
    if not entry.get(MARKER):
        return entry
    np = _np()
    name = entry.get("name")
    path = _npz_path(sdir, name) if name else None
    if np is None or not name or not path or not os.path.exists(path):
        return entry  # keep marker; cannot rehydrate now
    try:
        with np.load(path, allow_pickle=False) as z:
            if "embedding" in z.files:
                entry["embedding"] = z["embedding"].astype(float).tolist()
            spaces = {}
            for f in z.files:
                if f.startswith("sp_"):
                    spaces[f[3:]] = z[f].astype(float).tolist()
            if spaces:
                entry["embeddings"] = spaces
        entry.pop(MARKER, None)  # success — vectors are inline again
    except Exception:
        return entry  # corrupt/unreadable: keep marker, degrade this load
    return entry


def prune_orphans(sdir, live_names):
    """Delete sidecar files with no corresponding live entity. Returns count."""
    if not os.path.isdir(sdir):
        return 0
    live = set(live_names)
    n = 0
    for fn in os.listdir(sdir):
        if fn.endswith(".npz") and fn[:-4] not in live:
            try:
                os.unlink(os.path.join(sdir, fn))
                n += 1
            except OSError:
                pass
    return n
