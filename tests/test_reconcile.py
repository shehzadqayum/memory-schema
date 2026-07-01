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


def test_reconcile_empty_md_aborts_and_preserves(tmp_path):
    """SAFETY: an empty .md set (wrong root / parse regression) must ABORT, not wipe the store."""
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    with open(mem / "store.jsonl", "w", encoding="utf-8") as f:        # populated, but NO .md files
        for n in ("a", "b", "c"):
            f.write(json.dumps({"name": n, "description": n, "schema": 4}) + "\n")
    cfg = MemoryConfig(project_root=str(tmp_path),
                       neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")
    r = reconcile(cfg)                                                 # default allow_empty=False
    assert r.get("aborted")
    assert _jsonl_names(cfg) == {"a", "b", "c"}                        # store preserved, not wiped


def test_reconcile_voyage_down_degrades_not_crashes(tmp_path, monkeypatch):
    """Voyage down mid-reconcile: embed_failed is counted + captured in embed_errors, the name-set
    still heals (entity written without an embedding), and reconcile does not raise."""
    cfg = _setup(tmp_path, monkeypatch)                               # md={alpha,beta}, jsonl={alpha,ghost}
    monkeypatch.setattr(spaces, "embed_all_spaces",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("voyage down")))
    r = reconcile(cfg, prune=True, verify=True)
    assert r["embed_failed"] >= 1
    assert r.get("embed_errors")                                       # captured, not a silent counter
    assert _jsonl_names(cfg) == {"alpha", "beta"}                      # name-set still healed
    assert r["verify_jsonl_ok"] is True


_MALFORMED = ('<memory:entity schema="4" name="alpha">'
              '<memory:description>has a raw & ampersand which breaks XML parse</memory:description>'
              '</memory:entity>')


def test_reconcile_aborts_on_malformed_md_no_prune(tmp_path):
    """CORRUPTION GUARD: a .md that exists but fails to parse must ABORT reconcile and NOT prune its
    entity (a parse failure is not a deletion). Regression for the raw-& silent-prune bug."""
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "store.jsonl").write_text(
        json.dumps({"name": "alpha", "description": "A", "schema": 4}) + "\n", encoding="utf-8")
    (mem / "alpha.md").write_text(_MALFORMED, encoding="utf-8")     # exists, but won't parse
    cfg = MemoryConfig(project_root=str(tmp_path),
                       neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")
    r = reconcile(cfg)
    assert r.get("aborted")
    assert "alpha.md" in r["malformed"]
    assert _jsonl_names(cfg) == {"alpha"}                          # entity PRESERVED, not pruned


def test_diff_reports_malformed(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "store.jsonl").write_text(
        json.dumps({"name": "alpha", "schema": 4}) + "\n", encoding="utf-8")
    (mem / "alpha.md").write_text(_MALFORMED, encoding="utf-8")
    cfg = MemoryConfig(project_root=str(tmp_path),
                       neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")
    d = diff(cfg)
    assert "alpha.md" in d["malformed"]
    assert d["in_sync"] is False


def test_non_entity_md_not_flagged(tmp_path, monkeypatch):
    """A .md without a memory-entity tag (notes, README) is NOT corruption — skipped, not aborted."""
    cfg = _setup(tmp_path, monkeypatch)                            # md={alpha,beta}, jsonl={alpha,ghost}
    (tmp_path / "memory" / "notes.md").write_text("# just notes, not an entity\nhello", encoding="utf-8")
    r = reconcile(cfg, prune=True, verify=True)
    assert not r.get("malformed")
    assert not r.get("aborted")
    assert _jsonl_names(cfg) == {"alpha", "beta"}                  # heals normally


def test_reconcile_prunes_neo4j_orphan(tmp_path, monkeypatch):
    """Neo4j reachable with an orphan (no .md): reconcile deletes it (no-residuals) and pushes."""
    import memoryschema.migration as mig
    import memoryschema.neo4j_store as ns
    cfg = _setup(tmp_path, monkeypatch)                               # md={alpha,beta}

    class _FakeNeo4j:
        def __init__(self, names):
            self._names = set(names)
            self.deleted = []

        def list_all(self, include_inactive=False):
            return [{"name": n} for n in sorted(self._names)]

        def delete(self, name):
            self._names.discard(name)
            self.deleted.append(name)

        def compute_associations(self):
            pass

        def close(self):
            pass

    fake = _FakeNeo4j({"alpha", "ghost_neo"})                         # ghost_neo = Neo4j orphan
    monkeypatch.setattr(ns, "Neo4jMemoryStore", lambda config=None, **kw: fake)
    monkeypatch.setattr(mig, "migrate", lambda **kw: {"nodes_created": 0})
    r = reconcile(cfg, prune=True, verify=False)
    assert r["neo4j_reachable"] is True
    assert r["neo4j_pruned"] == 1
    assert "ghost_neo" in fake.deleted
    assert r["neo4j_pushed"] is True
