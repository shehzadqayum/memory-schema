"""Recall BFS semantics after the per-hop batched-cascade rewrite (Lever 1+1b).

Hermetic: instantiate Neo4jMemoryStore WITHOUT connecting (object.__new__) and mock the graph seams
(_vector_search, _get_neighbors_batch, _score_entry, embed_text). Asserts the must-test equivalence
cases: dedup-keeps-MAX-score, hop decay, association vs relation channel scoring, depth cap.
(hermetic test.)
"""
import pytest

import memoryschema.embeddings as embeddings
from memoryschema.neo4j_store import Neo4jMemoryStore


def _store():
    s = object.__new__(Neo4jMemoryStore)   # bypass __init__/connect — no live Neo4j
    s.config = None
    return s


def _ent(name):
    return {"name": name, "type": "semantic", "importance": 5, "status": "active",
            "description": name, "observations": [], "project": None}


@pytest.fixture
def store(monkeypatch):
    s = _store()
    monkeypatch.setattr(embeddings, "embed_text", lambda q, config=None: [1.0, 0.0])
    monkeypatch.setattr(s, "_vector_search", lambda emb, top_k=3, project=None: [_ent("A")])
    monkeypatch.setattr(s, "_searchable_text", lambda e: "")
    scores = {"A": 1.0, "B": 0.8, "C": 0.9, "D": 0.7, "E": 0.6, "F": 0.5}
    monkeypatch.setattr(s, "_score_entry", lambda e, qe=None, mode="semantic": scores[e["name"]])
    # A ->relation B; A ->assoc(0.5) C AND ->relation C (two paths to C); A ->assoc(0.5) F (assoc-only);
    # B ->relation D (hop2); D ->relation E (hop3, must be cut by depth)
    adj = {
        "A": [{"entry": _ent("B"), "channel": "relation", "rel_type": "USES"},
              {"entry": _ent("C"), "channel": "association", "assoc_score": 0.5},
              {"entry": _ent("C"), "channel": "relation", "rel_type": "USES"},
              {"entry": _ent("F"), "channel": "association", "assoc_score": 0.5}],
        "B": [{"entry": _ent("D"), "channel": "relation", "rel_type": "USES"}],
        "D": [{"entry": _ent("E"), "channel": "relation", "rel_type": "USES"}],
    }
    monkeypatch.setattr(s, "_get_neighbors_batch",
                        lambda names, project=None: {n: adj.get(n, []) for n in names})
    return s


def test_seed_and_hop_decay(store):
    by = {x["name"]: x for x in store.recall(query="x", depth=2, decay=0.8, limit=10)}
    assert by["A"]["score"] == 1.0 and by["A"]["channel"] == "seed" and by["A"]["hop"] == 0
    # B: hop1 relation = seed(1.0)*decay(0.8)*score(B=0.8) = 0.64
    assert by["B"]["score"] == round(1.0 * 0.8 * 0.8, 4) and by["B"]["channel"] == "relation"
    assert by["B"]["hop"] == 1


def test_dedup_keeps_max_score_and_winning_channel(store):
    by = {x["name"]: x for x in store.recall(query="x", depth=2, decay=0.8, limit=10)}
    # C reachable via relation (1.0*0.8*0.9=0.72) AND association (1.0*0.8*0.5=0.40) -> MAX wins
    assert by["C"]["score"] == round(1.0 * 0.8 * 0.9, 4)
    assert by["C"]["channel"] == "relation"          # higher-scoring path's channel


def test_association_channel_scoring(store):
    by = {x["name"]: x for x in store.recall(query="x", depth=2, decay=0.8, limit=10)}
    # F is association-only: score = hop_score * assoc_score = (1.0*0.8)*0.5 = 0.40 (NOT _score_entry)
    assert by["F"]["channel"] == "association"
    assert by["F"]["score"] == round(1.0 * 0.8 * 0.5, 4)


def test_hop2_and_depth_cap(store):
    by = {x["name"]: x for x in store.recall(query="x", depth=2, decay=0.8, limit=10)}
    # D: hop2 via B = (1.0*0.8*0.8 unrounded) * 0.8 * score(D=0.7)
    assert by["D"]["hop"] == 2
    assert by["D"]["score"] == round(1.0 * 0.8 * 0.8 * 0.8 * 0.7, 4)
    assert "E" not in by                              # hop3 cut by depth=2 (D not expanded)
