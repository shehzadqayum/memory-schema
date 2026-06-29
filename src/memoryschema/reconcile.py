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

from memoryschema.discovery import discover_memory_files
from memoryschema.store import MemoryStore
from memoryschema.tags import parse_memory_file


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
    if neo4j_store:
        neo4j_store.close()
    return {
        "md_count": len(md), "jsonl_count": len(jsonl), "neo4j_count": len(neo4j),
        "neo4j_error": neo4j_err,
        "missing_from_jsonl": sorted(md - jsonl),
        "jsonl_orphans": sorted(jsonl - md),
        "neo4j_orphans": sorted(neo4j - md) if neo4j_store else [],
        "in_sync": (md == jsonl) and (neo4j_store is None or neo4j == md),
    }


def reconcile(config, dry_run=False, prune=True, verify=True):
    """Make .md / JSONL / Neo4j agree exactly. Returns a result dict."""
    md_entities = _parse_md(config.memory_dir)
    md = set(md_entities)
    jstore = MemoryStore(str(config.store_path))
    jsonl_by_name = {e["name"]: e for e in jstore.list_all(include_inactive=True)}
    jsonl_names = set(jsonl_by_name)
    neo4j_store, neo4j_names, neo4j_err = _neo4j_names(config)

    result = {
        "md_count": len(md), "jsonl_count": len(jsonl_names), "neo4j_count": len(neo4j_names),
        "neo4j_error": neo4j_err,
        "missing_from_jsonl": sorted(md - jsonl_names),
        "jsonl_orphans": sorted(jsonl_names - md),
        "neo4j_orphans": sorted(neo4j_names - md),
        "reembedded": 0, "embed_failed": 0, "jsonl_pruned": 0, "neo4j_pruned": 0,
        "neo4j_pushed": False, "dry_run": dry_run,
    }

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
    from memoryschema.spaces import embed_all_spaces
    DERIVED = ("embedding", "embeddings", "divergence_profile",
               "created_at", "access_count", "last_accessed", "associations")
    final = []
    for name, e in md_entities.items():
        j = jsonl_by_name.get(name)
        if j and j.get("embedding") and _embed_text(j) == _embed_text(e):
            for k in DERIVED:                                   # reuse derived layer (full multi-space)
                if k in j and j[k] is not None:
                    e[k] = j[k]
        else:                                                   # new or content-changed -> re-embed all spaces
            try:
                embs, div = embed_all_spaces(e, config=config)
                if embs:
                    e["embeddings"] = embs
                    e["embedding"] = embs.get("default")
                    e["divergence_profile"] = div
                    result["reembedded"] += 1
                else:
                    result["embed_failed"] += 1                 # no embeddable text
            except Exception:
                result["embed_failed"] += 1                     # Voyage down -> degraded, not a crash
            if j and j.get("created_at"):
                e["created_at"] = j["created_at"]
        final.append(e)

    # --- 3: rewrite store.jsonl to EXACTLY the .md set (prunes JSONL residuals + applies edits) ---
    result["jsonl_pruned"] = len(jsonl_names - md)
    os.makedirs(os.path.dirname(str(config.store_path)) or ".", exist_ok=True)
    with open(str(config.store_path), "w", encoding="utf-8") as f:
        for e in final:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

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
            try:
                neo4j_store.compute_associations()
            except Exception:
                pass
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
