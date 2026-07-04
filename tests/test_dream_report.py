"""Tests for the dream-pass candidate report (read-only discovery)."""

import json

import pytest
from click.testing import CliRunner

from memoryschema.cli.main import cli
from memoryschema.config import MemoryConfig
from memoryschema.dream_report import build_report


@pytest.fixture
def project(tmp_path):
    (tmp_path / "memory").mkdir()
    return tmp_path


def _write_store(project, entries):
    with open(project / "memory" / "store.jsonl", "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


class TestBuildReport:
    def test_released_chain_is_candidate_active_is_not(self, project):
        _write_store(project, [
            {"name": "chain-released", "observations": ["Step 1: a"] * 12},
            {"name": "chain-current", "observations": ["Step 1: a"] * 5},
        ])
        cfg = MemoryConfig(project_root=project)
        r = build_report(cfg, active_chain="chain-current")
        assert [c["name"] for c in r["chains"]] == ["chain-released"]
        assert r["oversized"] == []          # active chain under threshold

    def test_oversized_active_chain(self, project):
        _write_store(project, [
            {"name": "chain-current", "observations": ["Step %d: x" % i for i in range(45)]},
        ])
        cfg = MemoryConfig(project_root=project)
        r = build_report(cfg, active_chain="chain-current")
        assert r["oversized"] and r["oversized"][0]["observations"] == 45

    def test_stale_keyed_fact(self, project):
        _write_store(project, [
            {"name": "old-bias", "key": "X.bias", "valid_from": "2026-06-01"},
            {"name": "fresh-bias", "key": "Y.bias", "valid_from": "2026-07-03"},
            {"name": "superseded-bias", "key": "Z.bias", "valid_from": "2026-05-01",
             "status": "superseded"},
        ])
        cfg = MemoryConfig(project_root=project)
        r = build_report(cfg, today="2026-07-05")
        names = [s["name"] for s in r["stale_keyed"]]
        assert names == ["old-bias"]         # fresh under 14d; superseded excluded
        assert r["stale_keyed"][0]["age_days"] == 34

    def test_duplicates_by_cosine(self, project):
        _write_store(project, [
            {"name": "a", "embedding": [1.0, 0.0, 0.0]},
            {"name": "b", "embedding": [0.99, 0.14, 0.0]},   # ~0.99 cosine with a
            {"name": "c", "embedding": [0.0, 1.0, 0.0]},     # orthogonal
        ])
        cfg = MemoryConfig(project_root=project)
        r = build_report(cfg, today="2026-07-05")
        pairs = {(d["a"], d["b"]) for d in r["duplicates"]}
        assert ("a", "b") in pairs
        assert all("c" not in p for p in pairs)

    def test_inactive_entries_excluded_everywhere(self, project):
        _write_store(project, [
            {"name": "chain-old", "status": "archived", "observations": ["Step 1: x"]},
            {"name": "dup-1", "status": "superseded", "embedding": [1, 0]},
            {"name": "dup-2", "status": "superseded", "embedding": [1, 0]},
        ])
        cfg = MemoryConfig(project_root=project)
        r = build_report(cfg, today="2026-07-05")
        assert sum(r["counts"].values()) == 0

    def test_never_surfaced_requires_log(self, project):
        # no recall log -> section stays empty (no false accusations)
        _write_store(project, [{"name": "quiet-fact", "description": "d"}])
        cfg = MemoryConfig(project_root=project)
        r = build_report(cfg, today="2026-07-05")
        assert r["never_surfaced"] == []

    def test_never_surfaced_reads_hits_shape(self, project, monkeypatch):
        # the REAL log schema: events carry "hits": [{"name": ...}] — a surfaced
        # entity must NOT be flagged (regression: the first live run flagged 41
        # actives, including entities recalled the same day, by reading the
        # wrong field name)
        _write_store(project, [{"name": "seen-fact", "description": "d"},
                               {"name": "unseen-fact", "description": "d"}])
        cfg = MemoryConfig(project_root=project)
        import memoryschema.dream_report as dr
        fake_events = [{"query": "q", "hits": [{"name": "seen-fact", "score": 0.7}]}]
        monkeypatch.setattr("memoryschema.recall_log.read_events",
                            lambda config: fake_events)
        r = dr.build_report(cfg, today="2026-07-05")
        flagged = [x["name"] for x in r["never_surfaced"]]
        assert "seen-fact" not in flagged
        assert "unseen-fact" in flagged


class TestDreamCLI:
    def test_empty_store_reads_consolidated(self, project):
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(project), "dream"])
        assert res.exit_code == 0, res.output
        assert "nothing to dream about" in res.output

    def test_report_renders_and_is_readonly(self, project):
        _write_store(project, [
            {"name": "chain-done", "observations": ["Step 1: x"] * 8},
        ])
        before = (project / "memory" / "store.jsonl").read_text(encoding="utf-8")
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(project), "dream"])
        assert res.exit_code == 0, res.output
        assert "chain-done" in res.output
        after = (project / "memory" / "store.jsonl").read_text(encoding="utf-8")
        assert after == before               # read-only guarantee

    def test_json_mode(self, project):
        _write_store(project, [{"name": "chain-x", "observations": ["Step 1: a"]}])
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(project), "dream", "--json"])
        data = json.loads(res.output)
        assert data["counts"]["chains"] == 1
