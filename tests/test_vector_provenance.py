"""Wide-review Cluster A regressions: operator commands must never destroy or desync vectors.

- reembed() on an externalized store must preserve the space vectors it did NOT recompute.
- reembed_all_spaces() must persist fresh vectors even when content (hence hash) is unchanged.
- Quarantine must pop embed_input_hash WITH the vectors (else old vectors get keyed as current).
- reconcile must not detach an intact sidecar when a row is marker-only (unrehydratable).
"""
import json
import os

import pytest

from memoryschema.config import MemoryConfig
from memoryschema.store import MemoryStore
from memoryschema import vector_sidecar

np = pytest.importorskip("numpy")


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "memory").mkdir()
    return MemoryConfig(project_root=str(tmp_path))


def _seed(cfg, extra=None):
    """One entity with default + a field-space vector, externalized to the sidecar."""
    store = MemoryStore(str(cfg.store_path), config=cfg)
    e = {"name": "ent-a", "schema": 5, "description": "alpha content",
         "observations": ["alpha content"],
         "embedding": [0.1, 0.2, 0.3, 0.4],
         "embeddings": {"default": [0.1, 0.2, 0.3, 0.4], "name": [0.9, 0.8, 0.7, 0.6]},
         "embed_input_hash": "H1"}
    if extra:
        e.update(extra)
    store.upsert(e)
    return store


def test_reembed_preserves_other_space_vectors(cfg, monkeypatch):
    _seed(cfg)
    # sanity: the store is externalized (raw row has no inline vectors)
    raw = json.loads(open(cfg.store_path, encoding="utf-8").readline())
    assert raw.get("vectors_external") and "embedding" not in raw

    import memoryschema.embeddings as emb
    monkeypatch.setattr(emb, "embed_batch",
                        lambda texts, config=None: [[0.5, 0.5, 0.5, 0.5] for _ in texts])
    from memoryschema.reembed import reembed
    stats = reembed(prefix="ent-", config=cfg, skip_assoc=True)
    assert stats["embedded"] == 1

    fresh = MemoryStore(str(cfg.store_path), config=cfg)._load()[0]
    assert fresh["embedding"] == pytest.approx([0.5, 0.5, 0.5, 0.5])   # recomputed default
    assert fresh["embeddings"]["name"] == pytest.approx([0.9, 0.8, 0.7, 0.6])  # OTHER space SURVIVES


def test_reembed_all_spaces_persists_fresh_vectors_when_content_unchanged(cfg, monkeypatch):
    store = _seed(cfg)
    import memoryschema.spaces as sp
    def fake_apply(entry, config=None):
        entry["embedding"] = [0.7, 0.7, 0.7, 0.7]
        entry["embeddings"] = {"default": [0.7, 0.7, 0.7, 0.7]}
        # content unchanged -> apply_full_embeddings re-stamps the SAME provenance hash
        return True
    monkeypatch.setattr(sp, "apply_full_embeddings", fake_apply)
    monkeypatch.setattr("memoryschema.reembed.apply_full_embeddings", fake_apply, raising=False)
    from memoryschema.reembed import reembed_all_spaces
    stats = reembed_all_spaces(config=cfg, store=store)
    assert stats["embedded"] == 1
    fresh = MemoryStore(str(cfg.store_path), config=cfg)._load()[0]
    assert fresh["embedding"] == pytest.approx([0.7, 0.7, 0.7, 0.7]), \
        "fresh vectors must be PERSISTED, not dropped by skip-if-unchanged"


def test_quarantine_upsert_keeps_old_hash_with_old_vectors(cfg):
    # the fixed callers pop vectors AND hash: the merged row must keep the OLD (V1,H1) pair,
    # never (V1, H2) — old vectors keyed as current would suppress the post-release re-embed
    store = _seed(cfg)
    store.upsert({"name": "ent-a", "schema": 5, "description": "edited content",
                  "observations": ["edited content"], "status": "quarantined"})
    row = store._load()[0]
    assert row.get("embed_input_hash") == "H1"                         # old hash stays with old vectors
    assert row.get("embedding") == pytest.approx([0.1, 0.2, 0.3, 0.4])


def test_reconcile_keeps_marker_when_row_is_unrehydratable(cfg, monkeypatch, tmp_path):
    # a marker-only row (rehydration unavailable: .npz temporarily unreadable) with a CURRENT
    # hash must keep its marker through reconcile — not be rewritten bare (sidecar detached)
    md = tmp_path / "memory" / "ent-b.md"
    md.write_text("---\nschema: 5\n---\n\nBeta content.\n", encoding="utf-8")
    from memoryschema.tags import parse_memory_file
    from memoryschema.embedding_input import embed_input_hash
    h = embed_input_hash(parse_memory_file(str(md)))
    with open(cfg.store_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"name": "ent-b", "schema": 5, "description": "Beta content.",
                            "vectors_external": True, "embed_input_hash": h}) + "\n")
    import memoryschema.spaces as sp
    def explode(entry, config=None):
        raise AssertionError("re-embed must NOT run for a current marker-only row")
    monkeypatch.setattr(sp, "apply_full_embeddings", explode)
    from memoryschema.reconcile import reconcile
    monkeypatch.setattr("memoryschema.reconcile.apply_full_embeddings", explode, raising=False)
    cfg2 = MemoryConfig(project_root=str(tmp_path),
                        neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")
    reconcile(cfg2)
    raw = [json.loads(l) for l in open(cfg2.store_path, encoding="utf-8") if l.strip()]
    row = {r["name"]: r for r in raw}["ent-b"]
    assert row.get("vectors_external") is True, "marker must survive reconcile (sidecar stays attached)"


# ── Cluster B: quarantine lifecycle is file-first (no resurrection, no re-quarantine) ────────
def test_quarantine_lifecycle_survives_reconcile(tmp_path, monkeypatch):
    from click.testing import CliRunner
    from memoryschema.cli.main import cli
    import memoryschema.write_gate as wg
    from memoryschema.write_gate import GateResult, GateVerdict

    (tmp_path / "memory").mkdir()
    md = tmp_path / "memory" / "q-ent.md"
    md.write_text("---\nschema: 5\n---\n\nQuarantine me.\n", encoding="utf-8")

    # force a QUARANTINE verdict at the production call site
    monkeypatch.setattr(wg, "gate_pipeline",
                        lambda memory, store=None, strict=False, config=None:
                        GateResult(GateVerdict.QUARANTINE, ["forced"], []))
    from memoryschema.write_index import index_memory
    cfg0 = MemoryConfig(project_root=str(tmp_path),
                        neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")
    res = index_memory(str(md), config=cfg0, require_active_chain_auth=False)
    assert res.verdict == "quarantine"

    # 1) file-first: the .md itself now carries the status
    assert "status: quarantined" in md.read_text(encoding="utf-8")

    # 2) reconcile must NOT resurrect (nor embed) it
    import memoryschema.spaces as sp
    monkeypatch.setattr(sp, "apply_full_embeddings",
                        lambda entry, config=None: (_ for _ in ()).throw(
                            AssertionError("reconcile must not embed a quarantined entity")))
    from memoryschema.reconcile import reconcile
    cfg = MemoryConfig(project_root=str(tmp_path),
                       neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")
    reconcile(cfg)
    row = [json.loads(l) for l in open(cfg.store_path, encoding="utf-8") if l.strip()][0]
    assert row["status"] == "quarantined" and not row.get("embedding")

    # 3) release flips the .md back to active; the next reconcile keeps it active
    runner = CliRunner()
    r = runner.invoke(cli, ["--root", str(tmp_path), "quarantine", "release", "q-ent"],
                      env={"MEMORYSCHEMA_SKIP_PREFLIGHT": "1",
                           "MEMORYSCHEMA_REQUIRE_NEO4J": "false",
                           "NEO4J_URI": "bolt://127.0.0.1:59999"})
    assert r.exit_code == 0, r.output
    assert "status: quarantined" not in md.read_text(encoding="utf-8")


# ── Cluster C: CLI safety ─────────────────────────────────────────────────────────────────────
def test_import_tar_requires_confirm(tmp_path):
    import tarfile
    from click.testing import CliRunner
    from memoryschema.cli.main import cli
    (tmp_path / "memory").mkdir()
    victim = tmp_path / "memory" / "keep.md"
    victim.write_text("---\nschema: 5\n---\n\nKeep me.\n", encoding="utf-8")
    tar_path = tmp_path / "foreign.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        clobber = tmp_path / "clobber.md"
        clobber.write_text("---\nschema: 5\n---\n\nFOREIGN.\n", encoding="utf-8")
        tar.add(clobber, arcname="memory/keep.md")
    r = CliRunner().invoke(cli, ["--root", str(tmp_path), "import", str(tar_path)],
                           env={"MEMORYSCHEMA_SKIP_PREFLIGHT": "1"})
    assert r.exit_code != 0 and "OVERWRITE" in r.output
    assert "Keep me." in victim.read_text(encoding="utf-8")   # nothing extracted without --confirm


def test_export_tar_arcnames_match_live_layout(tmp_path):
    import tarfile
    from click.testing import CliRunner
    from memoryschema.cli.main import cli
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "e.md").write_text("---\nschema: 5\n---\n\nE.\n", encoding="utf-8")
    (tmp_path / "memory" / "store.jsonl").write_text('{"name": "e", "schema": 5}\n', encoding="utf-8")
    out = tmp_path / "x.tar.gz"
    r = CliRunner().invoke(cli, ["--root", str(tmp_path), "export", "--format", "tar",
                                 "--output", str(out)],
                           env={"MEMORYSCHEMA_SKIP_PREFLIGHT": "1"})
    assert r.exit_code == 0, r.output
    with tarfile.open(out, "r:gz") as tar:
        names = tar.getnames()
    assert "memory/store.jsonl" in names                       # NOT root-level store.jsonl
    assert "memory/e.md" in names


def test_cli_env_autoload_is_allowlisted(tmp_path, monkeypatch):
    from memoryschema.cli.main import _load_project_env
    (tmp_path / ".env").write_text(
        "NEO4J_PASSWORD=pw\nVOYAGE_API_KEY=vk\nBROKER_SECRET=leakme\nGITHUB_TOKEN=gh\n",
        encoding="utf-8")
    for k in ("NEO4J_PASSWORD", "VOYAGE_API_KEY", "BROKER_SECRET", "GITHUB_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    _load_project_env(str(tmp_path))
    assert os.environ.get("NEO4J_PASSWORD") == "pw"
    assert os.environ.get("VOYAGE_API_KEY") == "vk"
    assert "BROKER_SECRET" not in os.environ                   # the allowlist holds
    assert "GITHUB_TOKEN" not in os.environ
    for k in ("NEO4J_PASSWORD", "VOYAGE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
