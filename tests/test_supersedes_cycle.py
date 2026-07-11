"""SUPERSEDES cycle detection (R7) — a cycle is REJECTED and the poison edge is NOT persisted.

Closes a zero-coverage gap: neither store had a cycle test, which is how the Neo4j check-after-commit
asymmetry survived (it MERGEd the edge, THEN checked — so a rejected cycle stayed in the graph). This is the
hermetic JSONL case; the Neo4j equivalent is an integration test in test_neo4j_store.py.
"""
import pytest

from memoryschema.store import MemoryStore


def _by_name(path, nm):
    for e in MemoryStore(path).list_all(include_inactive=True):
        if e.get("name") == nm:
            return e
    return None


def test_jsonl_supersedes_cycle_rejected_and_store_left_clean(tmp_path):
    p = str(tmp_path / "store.jsonl")
    s = MemoryStore(p)
    s.upsert({"name": "b", "schema": 5, "description": "d"})
    # a -> b : no cycle, persists (and flips b to superseded)
    s.upsert({"name": "a", "schema": 5, "description": "d",
              "relations": [{"type": "SUPERSEDES", "target": "b"}]})
    # b -> a : would close the cycle a -> b -> a
    with pytest.raises(ValueError, match="cycle"):
        s.upsert({"name": "b", "schema": 5, "description": "d",
                  "relations": [{"type": "SUPERSEDES", "target": "a"}]})
    # the poison edge must NOT be persisted, and the legit a -> b edge still stands
    b = _by_name(p, "a")   # 'a' holds the only SUPERSEDES edge; 'b' must have none back to 'a'
    b_entry = _by_name(p, "b")
    assert b_entry is not None
    assert not any(r.get("type") == "SUPERSEDES" and r.get("target") == "a"
                   for r in b_entry.get("relations", [])), "cyclic SUPERSEDES edge must not persist"
    assert any(r.get("type") == "SUPERSEDES" and r.get("target") == "b"
               for r in b.get("relations", [])), "the legit a->b edge must survive"
