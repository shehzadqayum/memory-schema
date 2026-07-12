"""Move 1: recall-usage telemetry — log_recall writes events; compute_stats summarises them.

The autouse conftest sets MEMORYSCHEMA_RECALL_LOG=0 (no telemetry during the suite), so these tests
re-enable it and use a tmp project so nothing touches a real log.
"""
import json

import pytest

from memoryschema.config import MemoryConfig
from memoryschema import recall_log


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.delenv("MEMORYSCHEMA_RECALL_LOG", raising=False)   # re-enable logging for these tests
    return MemoryConfig(project_root=str(tmp_path))


def _results():
    return [
        {"name": "alpha", "score": 0.71, "channel": "seed"},
        {"name": "beta", "score": 0.42, "channel": "association"},
    ]


def test_log_recall_appends_event(cfg):
    recall_log.log_recall(cfg, "a query", _results(), backend="Neo4jMemoryStore",
                          now="2026-06-30T10:00:00+00:00")
    ev = recall_log.read_events(cfg)
    assert len(ev) == 1
    assert ev[0]["query"] == "a query"
    assert ev[0]["n"] == 2
    assert ev[0]["backend"] == "Neo4jMemoryStore"
    assert ev[0]["hits"][0] == {"name": "alpha", "score": 0.71, "channel": "seed"}


def test_log_recall_snapshots_retrieval_config(cfg):
    # the cfg snapshot makes config changes visible in telemetry (attribution segmentable by regime)
    recall_log.log_recall(cfg, "q", _results(), backend="Neo4jMemoryStore",
                          now="2026-06-30T10:00:00+00:00")
    ev = recall_log.read_events(cfg)
    assert ev[0]["cfg"] == {"recency_decay": 0.995, "recall_depth": 2,
                            "recall_decay": 0.8, "semantic_weights": [0.2, 0.3, 0.5]}


def test_log_recall_disabled_writes_nothing(cfg, monkeypatch):
    monkeypatch.setenv("MEMORYSCHEMA_RECALL_LOG", "0")
    recall_log.log_recall(cfg, "q", _results(), backend="Neo4jMemoryStore")
    assert recall_log.read_events(cfg) == []


def test_log_recall_never_raises(cfg):
    # A junk results payload must not blow up the recall path.
    recall_log.log_recall(cfg, "q", [{"name": None, "score": None}], backend="x")
    recall_log.log_recall(cfg, "q", None, backend="x")
    assert isinstance(recall_log.read_events(cfg), list)


def test_compute_stats_summarises(cfg):
    recall_log.log_recall(cfg, "q1", _results(), backend="Neo4jMemoryStore",
                          now="2026-06-30T10:00:00+00:00")                       # strong (0.71)
    recall_log.log_recall(cfg, "q2", [{"name": "beta", "score": 0.30, "channel": "seed"}],
                          backend="MemoryStore", degraded=True,
                          now="2026-06-30T11:00:00+00:00")                       # weak + degraded
    recall_log.log_recall(cfg, "q3", [], backend="Neo4jMemoryStore",
                          now="2026-07-01T09:00:00+00:00")                       # no results
    s = recall_log.compute_stats(cfg, strong=0.5, known_names={"alpha", "beta", "gamma"})
    assert s["events"] == 3
    assert s["with_results"] == 2
    assert s["strong_hits"] == 1
    assert s["degraded"] == 1
    assert s["distinct_days"] == 2
    assert dict(s["top_surfaced"])["beta"] == 2
    assert s["never_surfaced_count"] == 1            # gamma never surfaced
    assert "gamma" in s["never_surfaced"]


def test_compute_stats_empty(cfg):
    s = recall_log.compute_stats(cfg)
    assert s["events"] == 0
    assert s["strong_hit_rate"] == 0.0
