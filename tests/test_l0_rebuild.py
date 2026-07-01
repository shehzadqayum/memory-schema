"""L0 self-heal: rebuild_index regenerates MEMORY.md as a faithful, status-filtered, importance-ranked
index of the store's ACTIVE set (helios local patch).

Regression for the drift where the append-only hook + evict-only budget lingered superseded/archived
entries and lost active ones, and reconcile ignored L0 entirely.
"""
import json

from memoryschema.l0_budget import rebuild_index, _truncate_desc, estimate_tokens


def _e(name, desc="d", type="semantic", importance=5, status="active"):
    return {"name": name, "description": desc, "type": type,
            "importance": importance, "status": status}


def _names_in(path):
    import re
    txt = open(path, encoding="utf-8").read()
    return [m.group(1) for m in re.finditer(r"^- \[([^\]]+)\]", txt, re.M)]


def test_rebuild_excludes_non_active(tmp_path):
    idx = tmp_path / "MEMORY.md"
    entries = [
        _e("alpha"), _e("beta"),
        _e("old", status="superseded"),
        _e("gone", status="archived"),
        _e("bad", status="quarantined"),
    ]
    r = rebuild_index(str(idx), entries=entries, token_budget=5000)
    assert r["written"] and r["total_active"] == 2 and r["kept"] == 2
    assert set(_names_in(idx)) == {"alpha", "beta"}           # non-active excluded


def test_rebuild_groups_and_ranks(tmp_path):
    idx = tmp_path / "MEMORY.md"
    entries = [
        _e("k-low", type="semantic", importance=3),
        _e("k-high", type="semantic", importance=9),
        _e("proc", type="procedural", importance=5),
        _e("sess", type="episodic", importance=5),
    ]
    rebuild_index(str(idx), entries=entries, token_budget=5000)
    txt = open(idx, encoding="utf-8").read()
    assert "### Knowledge" in txt and "### Procedures" in txt and "### Session History" in txt
    # within Knowledge, higher importance ranks first
    assert txt.index("k-high") < txt.index("k-low")
    # grouping: procedural entry sits under Procedures, not Knowledge
    assert txt.index("### Procedures") < txt.index("proc") < txt.index("### Session History")


def test_rebuild_budget_drops_lowest_importance(tmp_path):
    idx = tmp_path / "MEMORY.md"
    entries = [_e(f"m{i}", desc="x" * 100, importance=i) for i in range(1, 11)]
    r = rebuild_index(str(idx), entries=entries, token_budget=120)   # tiny -> must drop
    kept = set(_names_in(idx))
    assert r["dropped"]                                             # something dropped
    assert "m10" in kept and "m1" not in kept                      # highest kept, lowest dropped
    assert set(r["dropped"]).isdisjoint(kept)
    assert estimate_tokens(open(idx, encoding="utf-8").read()) <= 120
    assert "dropped for the L0 budget" in open(idx, encoding="utf-8").read()  # not silent


def test_rebuild_idempotent(tmp_path):
    idx = tmp_path / "MEMORY.md"
    entries = [_e("a", importance=7), _e("b", importance=4), _e("c", type="procedural")]
    rebuild_index(str(idx), entries=entries, token_budget=5000)
    first = open(idx, encoding="utf-8").read()
    rebuild_index(str(idx), entries=entries, token_budget=5000)
    assert open(idx, encoding="utf-8").read() == first             # byte-identical second run


def test_rebuild_from_store_path_active_only(tmp_path):
    store = tmp_path / "store.jsonl"
    with open(store, "w", encoding="utf-8") as f:
        f.write(json.dumps(_e("live", importance=6)) + "\n")
        f.write(json.dumps(_e("dead", status="superseded")) + "\n")
    idx = tmp_path / "MEMORY.md"
    r = rebuild_index(str(idx), store_path=str(store), token_budget=5000)
    assert r["kept"] == 1 and _names_in(idx) == ["live"]


def test_truncate_desc_collapses_and_bounds():
    assert _truncate_desc("a\nb   c") == "a b c"                   # newlines/runs collapsed
    long = "word " * 100
    out = _truncate_desc(long, width=40)
    assert len(out) <= 41 and out.endswith("…")                   # bounded + ellipsis
