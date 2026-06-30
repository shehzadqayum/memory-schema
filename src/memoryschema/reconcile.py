"""Reconcile the canonical memory/*.md set with the JSONL store and the Neo4j projection.

Layering: the .md files are CONTENT-truth; store.jsonl is the MATERIALIZED canonical
(it carries the derived layer — default + multi-space embeddings, divergence profile,
timestamps); Neo4j is a rebuildable projection of the JSONL.

reconcile() makes all three agree COMPLETELY and IDEMPOTENTLY:

  1. parse every .md (content);
  2. for each entity, REUSE the JSONL derived layer when the embedding-input text is
     unchanged (no wasted Voyage calls, preserves the full multi-space vectors);
     otherwise re-embed ALL spaces (new or content-changed entities);
  3. rewrite store.jsonl to EXACTLY the .md set (this prunes JSONL residuals and applies
     any content edits — the .md is authoritative);
  4. push the JSONL into Neo4j via the idempotent MERGE import (carries the embeddings);
  5. PRUNE Neo4j nodes with no .md (the no-residuals step);
  6. recompute associations; VERIFY by NAME-SET equality across .md / JSONL / Neo4j.

A second run on a clean store is a no-op (nothing changed, nothing re-embedded, nothing
pruned). If Voyage is down, new/changed entities are written without an embedding (loud
degraded path, not a crash). If Neo4j is down, the JSONL is still reconciled and Neo4j is
reported unreachable. helios local patch — re-apply on re-vendor.
"""
import json
import os
import tempfile

from memoryschema.discovery import discover_memory_files
from memoryschema.store import MemoryStore
from memoryschema.tags import parse_memory_file

# Safety: refuse to reconcile (which rewrites store.jsonl to EXACTLY the .md set and prunes Neo4j)
# when the parsed .md set has collapsed below this fraction of the existing JSONL — a misconfigured
# root or a parse regression would otherwise WIPE the store. Override per-call with allow_empty.
_SHRINK_GUARD_FRACTION = 0.5


def _atomic_write_jsonl(path, entries):
    """Write `entries` to `path` atomically: a sibling tmp file + os.replace, so a crash mid-write
    can never leave a truncated/half-written store."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".store.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _embed_text(entry):
    """The default-space embedding-input text — the change-detection key."""
    from memoryschema.embedding_input import compose_embedding_text
    return compose_embedding_text(entry)


def _parse_md(memory_dir):
    """{name: parsed entity} from the canonical .md files (non-entity files skipped)."""
    out = {}
    for fp in discover_memory_files(str(memory_dir)):
        m = parse_memory_file(fp)
        if m and m.get("name"):
            out[m["name"]] = m
    return out


def _neo4j_names(config):
    """(store_or_None, names_set, error_or_None) for the Neo4j projection."""
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore(config=config)
        names = {e["name"] for e in store.list_all(include_inactive=True)}
        return store, names, None
    except Exception as e:
        return None, set(), str(e)


def diff(config):
    """Read-only drift report across .md / JSONL / Neo4j (the real `sync`)."""
    md = set(_parse_md(config.memory_dir))
    jsonl = {e["name"] for e in MemoryStore(str(config.store_path)).list_all(include_inactive=True)}
    neo4j_store, neo4j, neo4j_err = _neo4j_names(config)
    reachable = neo4j_store is not None      # explicit flag — never reuse a closed handle for this
    if neo4j_store:
        neo4j_store.close()
    return {
        "md_count": len(md), "jsonl_count": len(jsonl),
        "neo4j_count": (len(neo4j) if reachable else None),    # None, not 0 — "down" != "empty"
        "neo4j_reachable": reachable, "neo4j_error": neo4j_err,
        "missing_from_jsonl": sorted(md - jsonl),
        "jsonl_orphans": sorted(jsonl - md),
        "neo4j_orphans": (sorted(neo4j - md) if reachable else None),
        "in_sync": (md == jsonl) and (not reachable or neo4j == md),
    }


def reconcile(config, dry_run=False, prune=True, verify=True, allow_empty=False):
    """Make .md / JSONL / Neo4j agree exactly. Returns a result dict.

    allow_empty: bypass the shrink/empty safety guard (only when an empty-or-collapsed .md set
    is genuinely intended, e.g. a deliberate bulk delete).
    """
    md_entities = _parse_md(config.memory_dir)
    md = set(md_entities)
    jstore = MemoryStore(str(config.store_path))
    jsonl_by_name = {e["name"]: e for e in jstore.list_all(include_inactive=True)}
    jsonl_names = set(jsonl_by_name)
    neo4j_store, neo4j_names, neo4j_err = _neo4j_names(config)
    neo4j_reachable = neo4j_store is not None

    result = {
        "md_count": len(md), "jsonl_count": len(jsonl_names),
        "neo4j_count": (len(neo4j_names) if neo4j_reachable else None),
        "neo4j_reachable": neo4j_reachable, "neo4j_error": neo4j_err,
        "missing_from_jsonl": sorted(md - jsonl_names),
        "jsonl_orphans": sorted(jsonl_names - md),
        "neo4j_orphans": (sorted(neo4j_names - md) if neo4j_reachable else None),
        "reembedded": 0, "embed_failed": 0, "jsonl_pruned": 0, "neo4j_pruned": 0,
        "neo4j_pushed": False, "dry_run": dry_run,
    }

    # SAFETY GUARD: reconcile rewrites store.jsonl to EXACTLY the .md set and prunes Neo4j orphans,
    # so an empty/collapsed .md set (wrong root, missing dir, parse regression) would WIPE the store.
    # Refuse unless the collapse is explicitly intended.
    if not dry_run and not allow_empty:
        shrunk = bool(jsonl_names) and len(md) < int(len(jsonl_names) * _SHRINK_GUARD_FRACTION)
        if not md or shrunk:
            result["aborted"] = (
                f"refusing to reconcile: {len(md)} .md entit(ies) vs {len(jsonl_names)} in JSONL — "
                f"{'empty .md set' if not md else 'shrank past the safety guard'}. "
                f"If intended, re-run with --allow-empty."
            )
            if neo4j_store is not None:
                neo4j_store.close()
            return result

    if dry_run:
        # report which entities would be re-embedded (new or content-changed)
        changed = 0
        for name, e in md_entities.items():
            j = jsonl_by_name.get(name)
            if not (j and j.get("embedding") and _embed_text(j) == _embed_text(e)):
                changed += 1
        result["would_reembed"] = changed
        if neo4j_store:
            neo4j_store.close()
        return result

    # --- 1+2: build the exact .md set, reusing the JSONL derived layer where unchanged ---
    from memoryschema.spaces import apply_full_embeddings
    DERIVED = ("embedding", "embeddings", "divergence_profile",
               "created_at", "access_count", "last_accessed", "associations")
    final = []
    for name, e in md_entities.items():
        out = dict(e)                                           # fresh dict — keep parsed .md pristine
        j = jsonl_by_name.get(name)
        if j and j.get("embedding") and _embed_text(j) == _embed_text(e):
            for k in DERIVED:                                   # reuse derived layer (full multi-space)
                if k in j and j[k] is not None:
                    out[k] = j[k]
        else:                                                   # new or content-changed -> re-embed all spaces
            try:
                if apply_full_embeddings(out, config=config):
                    result["reembedded"] += 1
                else:
                    result["embed_failed"] += 1                 # no embeddable text
            except Exception as ex:
                result["embed_failed"] += 1                     # Voyage down -> degraded, not a crash
                result.setdefault("embed_errors", []).append((name, str(ex)[:120]))
            if j and j.get("created_at"):
                out["created_at"] = j["created_at"]
        final.append(out)

    # --- 3: rewrite store.jsonl to EXACTLY the .md set (prunes JSONL residuals + applies edits) ---
    result["jsonl_pruned"] = len(jsonl_names - md)
    _atomic_write_jsonl(str(config.store_path), final)          # tmp + os.replace (crash-safe)

    # --- 4+5: push JSONL -> Neo4j (idempotent MERGE) + prune Neo4j orphans ---
    if neo4j_store is not None:
        try:
            from memoryschema.migration import migrate as _migrate
            _migrate(config=config, dry_run=False)              # carries the embeddings from JSONL
            if prune:
                # re-list AFTER the import so any relation-target stub nodes it MERGEd are pruned too
                post = {e["name"] for e in neo4j_store.list_all(include_inactive=True)}
                for name in (post - md):
                    neo4j_store.delete(name)
                result["neo4j_pruned"] = len(post - md)
            changed = bool(result["reembedded"] or result["jsonl_pruned"]
                           or result["neo4j_pruned"] or result["missing_from_jsonl"])
            result["associations_recomputed"] = changed
            if changed:                                         # skip the O(n^2) recompute on a no-op
                try:
                    neo4j_store.compute_associations()
                except Exception as ex:
                    result["assoc_error"] = str(ex)[:160]
                    result["associations_recomputed"] = False
            result["neo4j_pushed"] = True
        except Exception as e:
            result["neo4j_push_error"] = str(e)

    # --- 6: verify by name-set ---
    if verify:
        jset = {x["name"] for x in MemoryStore(str(config.store_path)).list_all(include_inactive=True)}
        result["verify_jsonl_ok"] = (jset == md)
        if neo4j_store is not None and result["neo4j_pushed"]:
            nset = {x["name"] for x in neo4j_store.list_all(include_inactive=True)}
            result["verify_neo4j_ok"] = (nset == md)
            result["verify_ok"] = (jset == md == nset)
            result["verify_extra"] = sorted((jset | nset) - md)
            result["verify_missing"] = sorted(md - (jset & nset))
        else:
            result["verify_ok"] = (jset == md)
            result["verify_extra"] = sorted(jset - md)
            result["verify_missing"] = sorted(md - jset)

    if neo4j_store is not None:
        neo4j_store.close()
    return result
