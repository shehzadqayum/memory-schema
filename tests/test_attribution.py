"""Tests for attribution sampling (citation logging + recall-join) and the
promotion machinery (promoted_to lifecycle + dream-report sections)."""

import json
import os

import pytest
from click.testing import CliRunner

from memoryschema.attribution import compute_attribution, log_citation, read_citations
from memoryschema.cli.main import cli
from memoryschema.config import MemoryConfig
from memoryschema.dream_report import build_report


@pytest.fixture
def project(tmp_path):
    (tmp_path / "memory").mkdir()
    return tmp_path


def _cfg(project):
    return MemoryConfig(project_root=project)


def _write_recall_log(project, events):
    d = project / ".memoryschema"
    d.mkdir(exist_ok=True)
    with open(d / "recall_log.jsonl", "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class TestCitationLog:
    def test_log_and_read(self, project):
        cfg = _cfg(project)
        log_citation(cfg, source="chain-x", targets=["mem-a", "mem-b"], context="chain-step")
        evs = read_citations(cfg)
        assert len(evs) == 2
        assert {e["target"] for e in evs} == {"mem-a", "mem-b"}
        assert all(e["source"] == "chain-x" and e["ts"] for e in evs)

    def test_empty_targets_noop(self, project):
        cfg = _cfg(project)
        log_citation(cfg, source="x", targets=[])
        assert read_citations(cfg) == []


class TestComputeAttribution:
    def test_recall_then_cite_within_window_attributes(self, project):
        cfg = _cfg(project)
        _write_recall_log(project, [
            {"ts": "2026-07-05T10:00:00+00:00", "query": "q",
             "hits": [{"name": "mem-a", "score": 0.7}, {"name": "mem-b", "score": 0.6}]},
        ])
        d = project / ".memoryschema"
        with open(d / "citation_log.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": "2026-07-05T12:00:00+00:00",
                                "source": "chain-y", "target": "mem-a"}) + "\n")
        rep = compute_attribution(cfg)
        a = rep["memories"]["mem-a"]
        assert a["recalls"] == 1 and a["citations"] == 1
        assert a["attributed_recalls"] == 1 and a["attribution_rate"] == 1.0
        b = rep["memories"]["mem-b"]
        assert b["citations"] == 0 and b["attribution_rate"] == 0.0

    def test_cite_outside_window_not_attributed(self, project):
        cfg = _cfg(project)
        _write_recall_log(project, [
            {"ts": "2026-07-01T10:00:00+00:00", "query": "q",
             "hits": [{"name": "mem-a", "score": 0.7}]},
        ])
        d = project / ".memoryschema"
        with open(d / "citation_log.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": "2026-07-05T10:00:00+00:00",
                                "source": "s", "target": "mem-a"}) + "\n")
        rep = compute_attribution(cfg)
        a = rep["memories"]["mem-a"]
        assert a["citations"] == 1 and a["attributed_recalls"] == 0

    def test_recalled_never_cited_summary(self, project):
        cfg = _cfg(project)
        _write_recall_log(project, [
            {"ts": "2026-07-0%dT10:00:00+00:00" % i, "query": "q",
             "hits": [{"name": "noisy-mem", "score": 0.6}]} for i in range(1, 5)
        ])
        rep = compute_attribution(cfg)
        assert "noisy-mem" in rep["summary"]["recalled_never_cited"]


class TestCLICitationWiring:
    def test_remember_uses_logs_citation(self, project, monkeypatch):
        monkeypatch.setenv("MEMORYSCHEMA_V5", "1")
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(project), "remember", "new-fact",
                                  "--desc", "d", "--obs", "o", "--uses", "evidence-x"])
        assert res.exit_code == 0, res.output
        evs = read_citations(_cfg(project))
        assert [e["target"] for e in evs] == ["evidence-x"]
        assert evs[0]["context"] == "remember"

    def test_chain_step_uses_logs_citation(self, project):
        (project / "memory" / ".active_chain").write_text("chain-t", encoding="utf-8")
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(project), "chain", "step", "text",
                                  "--uses", "cited-mem"])
        assert res.exit_code == 0, res.output
        evs = read_citations(_cfg(project))
        assert [e["target"] for e in evs] == ["cited-mem"]
        assert evs[0]["context"] == "chain-step"

    def test_attribution_command_renders(self, project):
        _write_recall_log(project, [
            {"ts": "2026-07-05T10:00:00+00:00", "query": "q",
             "hits": [{"name": "mem-a", "score": 0.7}]},
        ])
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(project), "attribution"])
        assert res.exit_code == 0, res.output
        assert "mem-a" in res.output


class TestPromotionMachinery:
    def _store(self, project, entries):
        with open(project / "memory" / "store.jsonl", "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_procedural_unpromoted_is_candidate(self, project):
        self._store(project, [
            {"name": "proc-rule", "type": "procedural", "description": "d"},
            {"name": "proc-done", "type": "procedural", "promoted_to": "CLAUDE.md"},
            {"name": "plain-fact", "type": "semantic"},
        ])
        r = build_report(_cfg(project), today="2026-07-05")
        names = [c["name"] for c in r["promotion_candidates"]]
        assert names == ["proc-rule"]        # promoted + semantic excluded

    def test_much_cited_is_candidate(self, project):
        self._store(project, [{"name": "hot-mem", "type": "semantic"}])
        d = project / ".memoryschema"
        d.mkdir(exist_ok=True)
        with open(d / "citation_log.jsonl", "w", encoding="utf-8") as f:
            for i in range(3):
                f.write(json.dumps({"ts": "2026-07-05T10:0%d:00+00:00" % i,
                                    "source": "s%d" % i, "target": "hot-mem"}) + "\n")
        r = build_report(_cfg(project), today="2026-07-05")
        assert [c["name"] for c in r["promotion_candidates"]] == ["hot-mem"]

    def test_promoted_to_roundtrip(self, project, monkeypatch):
        from memoryschema.format_v5 import parse_v5_content, serialize_v5
        from memoryschema.write_index import set_lifecycle
        m = {"schema": 5, "name": "p", "description": "d", "observations": ["o"]}
        p = project / "memory" / "p.md"
        p.write_text(serialize_v5(m), encoding="utf-8")
        set_lifecycle(str(p), promoted_to="CLAUDE.md#journal")
        back = parse_v5_content(p.read_text(encoding="utf-8"), filepath=str(p))
        assert back["promoted_to"] == "CLAUDE.md#journal"

    def test_attribution_review_section(self, project):
        self._store(project, [{"name": "noisy-mem", "type": "semantic"}])
        _write_recall_log(project, [
            {"ts": "2026-07-0%dT10:00:00+00:00" % i, "query": "q",
             "hits": [{"name": "noisy-mem", "score": 0.6}]} for i in range(1, 5)
        ])
        r = build_report(_cfg(project), today="2026-07-05")
        assert [c["name"] for c in r["attribution_review"]] == ["noisy-mem"]


class TestStoreMergePreservesLifecycle:
    """The JSONL merge whitelist must carry the lifecycle/temporal fields —
    set_lifecycle + re-index updates an EXISTING entity, so a whitelist miss
    silently drops them until the next reconcile (found live: promoted_to
    vanished on the first real promotion)."""

    def test_upsert_merge_keeps_lifecycle_fields(self, project):
        from memoryschema.store import MemoryStore
        sp = project / "memory" / "store.jsonl"
        store = MemoryStore(str(sp))
        store.upsert({"name": "m", "description": "d"})
        store.upsert({"name": "m", "description": "d",
                      "promoted_to": "CLAUDE.md#x", "key": "config.timeout",
                      "valid_from": "2026-07-01", "superseded_at": "2026-07-02",
                      "superseded_by": "successor"})
        entry = next(json.loads(l) for l in open(sp, encoding="utf-8")
                     if json.loads(l).get("name") == "m")
        assert entry["promoted_to"] == "CLAUDE.md#x"
        assert entry["key"] == "config.timeout"
        assert entry["valid_from"] == "2026-07-01"
        assert entry["superseded_at"] == "2026-07-02"
        assert entry["superseded_by"] == "successor"


class TestNeverSurfacedGrace:
    def test_fresh_entity_not_flagged(self, project):
        with open(project / "memory" / "store.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"name": "fresh-mem", "description": "d",
                                "created_at": "2026-07-04T10:00:00+00:00"}) + "\n")
            f.write(json.dumps({"name": "old-mem", "description": "d",
                                "created_at": "2026-06-01T10:00:00+00:00"}) + "\n")
        _write_recall_log(project, [
            {"ts": "2026-07-05T10:00:00+00:00", "query": "q",
             "hits": [{"name": "unrelated", "score": 0.5}]},
        ])
        r = build_report(_cfg(project), today="2026-07-05")
        names = [c["name"] for c in r["never_surfaced"]]
        assert "old-mem" in names and "fresh-mem" not in names


def _write_citation_log(project, events):
    d = project / ".memoryschema"
    d.mkdir(exist_ok=True)
    with open(d / "citation_log.jsonl", "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class TestAggregateAndDrift:
    def test_aggregate_event_level_rate_per_window(self, project):
        from memoryschema.attribution import compute_aggregate
        # ev1: hit cited +2h (attributed at all windows); ev2: hit cited +48h (only 72h/168h);
        # ev3: hit never cited (never attributed).
        _write_recall_log(project, [
            {"ts": "2026-07-01T10:00:00", "hits": [{"name": "a"}]},
            {"ts": "2026-07-02T10:00:00", "hits": [{"name": "b"}]},
            {"ts": "2026-07-03T10:00:00", "hits": [{"name": "c"}]},
        ])
        _write_citation_log(project, [
            {"ts": "2026-07-01T12:00:00", "target": "a"},
            {"ts": "2026-07-04T10:00:00", "target": "b"},   # +48h after ev2
        ])
        agg = compute_aggregate(_cfg(project), windows=(24, 72, 168))
        assert agg["events"] == 3
        assert agg["overall"]["24"]["attributed"] == 1      # only a
        assert agg["overall"]["72"]["attributed"] == 2      # a + b
        assert agg["overall"]["24"]["rate"] == round(1 / 3, 3)

    def test_aggregate_segments_by_config_regime(self, project):
        from memoryschema.attribution import compute_aggregate
        cfgA = {"recency_decay": 0.995, "recall_depth": 2}
        cfgB = {"recency_decay": 0.99, "recall_depth": 2}
        _write_recall_log(project, [
            {"ts": "2026-07-01T10:00:00", "hits": [{"name": "a"}], "cfg": cfgA},
            {"ts": "2026-07-02T10:00:00", "hits": [{"name": "b"}], "cfg": cfgB},
            {"ts": "2026-07-03T10:00:00", "hits": [{"name": "c"}]},   # no cfg -> pre-cfg
        ])
        _write_citation_log(project, [{"ts": "2026-07-01T12:00:00", "target": "a"}])
        agg = compute_aggregate(_cfg(project), windows=(24,))
        assert set(agg["by_regime"]) == {
            json.dumps(cfgA, sort_keys=True), json.dumps(cfgB, sort_keys=True), "pre-cfg"}
        assert agg["by_regime"][json.dumps(cfgA, sort_keys=True)]["24"]["rate"] == 1.0
        assert agg["by_regime"]["pre-cfg"]["24"]["rate"] == 0.0

    def test_drift_alarm_fires_on_a_fall(self, project):
        from memoryschema.attribution import attribution_drift
        # prior 14d: 2 events both attributed (rate 1.0); recent 14d: 2 events none attributed (0.0)
        _write_recall_log(project, [
            {"ts": "2026-06-05T10:00:00", "hits": [{"name": "p1"}]},
            {"ts": "2026-06-06T10:00:00", "hits": [{"name": "p2"}]},
            {"ts": "2026-06-25T10:00:00", "hits": [{"name": "r1"}]},
            {"ts": "2026-06-26T10:00:00", "hits": [{"name": "r2"}]},
        ])
        _write_citation_log(project, [
            {"ts": "2026-06-05T11:00:00", "target": "p1"},
            {"ts": "2026-06-06T11:00:00", "target": "p2"},
        ])
        d = attribution_drift(_cfg(project), window_hours=24, period_days=14, now="2026-07-02T10:00:00")
        assert d["prior"] == 1.0 and d["recent"] == 0.0 and d["rel_drop"] == 1.0

    def test_drift_none_when_a_period_is_empty(self, project):
        from memoryschema.attribution import attribution_drift
        _write_recall_log(project, [{"ts": "2026-07-01T10:00:00", "hits": [{"name": "a"}]}])
        d = attribution_drift(_cfg(project), now="2026-07-02T10:00:00")
        assert d["prior"] is None and d["rel_drop"] is None
