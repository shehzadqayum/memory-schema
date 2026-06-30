"""P2: reconcile must heal drift completely (no residuals) and be idempotent.

Hermetic: a tmp project with .md files + a drifted store.jsonl, a bogus Neo4j URI (so the
Neo4j path is skipped), and a mocked embedder (no Voyage). Asserts that JSONL is rewritten
to EXACTLY the .md name-set (orphans pruned, missing added) and that a second run is a no-op.
(helios local patch test.)
"""
import json

import memoryschema.spaces as spaces
from memoryschema.config import MemoryConfig
from memoryschema.reconcile import diff, reconcile

_ENTITY = (
    '<memory:entity schema="4" name="{name}" type="semantic" importance="5">\n'
    '  <memory:description>{desc}</memory:description>\n'
    '  <memory:observations>\n'
    '    <memory:observation>obs for {name}</memory:observation>\n'
    '  </memory:observations>\n'
    '</memory:entity>\n'
)


def _setup(tmp_path, monkeypatch):
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    # canonical .md set = {alpha, beta}
    (mem / "alpha.md").write_text(_ENTITY.format(name="alpha", desc="Alpha entity"), encoding="utf-8")
    (mem / "beta.md").write_text(_ENTITY.format(name="beta", desc="Beta entity"), encoding="utf-8")
    # drifted JSONL: has alpha (embedded) + ghost orphan (no .md); missing beta
    with open(mem / "store.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"name": "alpha", "description": "Alpha entity",
                            "observations": ["obs for alpha"], "embedding": [0.1] * 8, "schema": 4}) + "\n")
        f.write(json.dumps({"name": "ghost", "description": "orphan",
                            "observations": [], "embedding": [0.2] * 8, "schema": 4}) + "\n")
    # deterministic embedder (no Voyage) so 'beta' (new) can be embedded
    monkeypatch.setattr(spaces, "embed_all_spaces", lambda entry, **kw: ({"default": [0.3] * 8}, {}))
    # bogus Neo4j -> reconcile's neo4j path is skipped (no live backend touched)
    return MemoryConfig(project_root=str(tmp_path),
                        neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")


def _jsonl_names(cfg):
    return {json.loads(l)["name"] for l in open(cfg.store_path, encoding="utf-8") if l.strip()}


def test_diff_detects_drift(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)
    d = diff(cfg)
    assert d["missing_from_jsonl"] == ["beta"]
    assert d["jsonl_orphans"] == ["ghost"]
    assert d["in_sync"] is False


def test_reconcile_heals_to_md_no_residuals(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)
    r = reconcile(cfg, prune=True, verify=True)
    assert _jsonl_names(cfg) == {"alpha", "beta"}        # ghost pruned, beta added
    assert r["jsonl_pruned"] == 1
    assert r["reembedded"] >= 1                          # beta (new) embedded
    assert r["verify_jsonl_ok"] is True


def test_reconcile_is_idempotent(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)
    reconcile(cfg, prune=True, verify=True)
    r2 = reconcile(cfg, prune=True, verify=True)         # second run = no-op
    assert r2["reembedded"] == 0
    assert r2["jsonl_pruned"] == 0
    assert r2["verify_jsonl_ok"] is True
    assert _jsonl_names(cfg) == {"alpha", "beta"}
