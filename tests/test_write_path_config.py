"""Fractal acceptance-test bug: every write path constructed Neo4jMemoryStore() BARE, ignoring
memoryschema.toml — wrong bolt uri/port -> auth fail -> silent JSONL-only degradation on every
write (remember / chain step / hook), while the read/heal paths loaded the toml correctly and
masked it. index_memory must thread the TOML-loaded config into the Neo4j construction."""


def test_index_memory_passes_toml_config_to_neo4j(tmp_path, monkeypatch):
    import memoryschema.write_index as wi
    import memoryschema.neo4j_store as ns

    # the hermetic conftest pins NEO4J_URI; clear it so TOML precedence is what we observe
    monkeypatch.delenv("NEO4J_URI", raising=False)

    (tmp_path / "memory").mkdir()
    md = tmp_path / "memory" / "cfg-ent.md"
    md.write_text("---\nschema: 5\n---\n\nConfig threading test.\n", encoding="utf-8")
    (tmp_path / "memoryschema.toml").write_text(
        '[project]\nname = "cfgtest"\n\n[neo4j]\nuri = "bolt://localhost:7699"\n',
        encoding="utf-8")

    captured = {}

    class FakeNeo4j:
        def __init__(self, *a, **kw):
            captured["config"] = kw.get("config")
            raise ConnectionError("construction kwargs are what we assert")

    monkeypatch.setattr(ns, "Neo4jMemoryStore", FakeNeo4j)
    res = wi.index_memory(str(md), require_active_chain_auth=False)

    assert res.ok                                             # JSONL fallback still indexes
    assert captured.get("config") is not None, "Neo4jMemoryStore must receive config"
    assert captured["config"].neo4j_uri == "bolt://localhost:7699", \
        "config must come from memoryschema.toml (from_toml), not the bare constructor"
    assert any("7699" in w or "ConnectionError" in w for w in res.warnings), \
        "the degradation warning must carry the exception detail, not just the type name"
