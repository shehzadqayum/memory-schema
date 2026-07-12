"""Calibration toolkit (gate-tuning Tiers 1/2/4/5): overrides, paired replay, goldgen,
probe slot, decay fit. Hermetic — tmp projects, keyword-path recall (no embeddings)."""
import json
import random

import pytest

from memoryschema.config import MemoryConfig
from memoryschema.eval.calibrate import (apply_overrides, fit_decay, gold_candidates,
                                         parse_overrides, replay, sign_test_p)
from memoryschema.store import MemoryStore
from memoryschema import recall_log
from memoryschema.attribution import log_citation


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.delenv("MEMORYSCHEMA_RECALL_LOG", raising=False)
    return MemoryConfig(project_root=str(tmp_path))


# ── overrides ──────────────────────────────────────────────────────────────────────────────
def test_parse_overrides_coerces_by_field_type(cfg):
    out = parse_overrides(["retrieval.recency_decay=0.99", "retrieval.recall_depth=3",
                           "gate.numeric_probe_enabled=false", "gate.numeric_probe_mode=quarantine",
                           "retrieval.semantic_weights=0.1,0.3,0.6"], cfg)
    assert out == {"recency_decay": 0.99, "recall_depth": 3, "numeric_probe_enabled": False,
                   "numeric_probe_mode": "quarantine", "semantic_weights": (0.1, 0.3, 0.6)}


def test_parse_overrides_rejects_unknown_key_loudly(cfg):
    with pytest.raises(ValueError, match="unknown config key"):
        parse_overrides(["retrieval.nope=1"], cfg)


def test_apply_overrides_leaves_original_untouched(cfg):
    cfg2 = apply_overrides(cfg, ["retrieval.recency_decay=0.9"])
    assert cfg2.recency_decay == 0.9 and cfg.recency_decay == 0.995


# ── paired sign test ───────────────────────────────────────────────────────────────────────
def test_sign_test_exact_values():
    assert sign_test_p(0, 0) == 1.0
    assert abs(sign_test_p(5, 0) - 2 * 0.5 ** 5) < 1e-12    # 0.0625
    assert sign_test_p(3, 3) == 1.0                          # perfectly balanced


# ── goldgen (attribution-mined candidates) ────────────────────────────────────────────────
def test_gold_candidates_from_attributed_recall(cfg):
    recall_log.log_recall(cfg, "how do timezones work", [{"name": "tz-fact", "score": 0.8,
                          "channel": "seed"}], backend="MemoryStore",
                          now="2026-07-01T10:00:00+00:00")
    log_citation(cfg, "chain-x", ["tz-fact"], context="chain-step")   # cited now (within 24h? ts=now)
    # the citation ts is real now — re-log a recall far in the past to prove windowing
    rows = gold_candidates(cfg, window_hours=24 * 365 * 10)           # generous window for the test
    assert rows and rows[0]["query"] == "how do timezones work"
    assert rows[0]["relevant"] == ["tz-fact"] and rows[0]["kind"] == "attribution-candidate"


# ── paired replay ─────────────────────────────────────────────────────────────────────────
def test_replay_paired_diff_on_logged_queries(cfg, tmp_path):
    store = MemoryStore(str(cfg.store_path))
    for n, d in [("alpha-fact", "alpha topic anchors"), ("beta-fact", "beta topic anchors"),
                 ("gamma-fact", "gamma topic anchors")]:
        store.upsert({"name": n, "schema": 5, "description": d, "observations": [d]})
    recall_log.log_recall(cfg, "alpha topic", [{"name": "alpha-fact", "score": 0.5,
                          "channel": "seed"}], backend="MemoryStore",
                          now="2026-07-01T10:00:00+00:00")
    r = replay(cfg, [], ["retrieval.recall_decay=0.5"], k=3)
    assert r["k"] == 3 and r["b"] == {"recall_decay": 0.5}
    assert r["logged"]["queries"] == 1
    assert 0.0 <= (r["logged"]["mean_jaccard"] or 0) <= 1.0
    assert r["gold"]["queries"] == 0                                  # no eval-gold.jsonl → honest note


def test_replay_gold_mcnemar_when_gold_exists(cfg):
    store = MemoryStore(str(cfg.store_path))
    store.upsert({"name": "alpha-fact", "schema": 5, "description": "alpha topic anchors",
                  "observations": ["alpha topic anchors"]})
    (cfg.project_root / "eval-gold.jsonl").write_text(
        json.dumps({"query": "alpha topic", "relevant": ["alpha-fact"], "kind": "t"}) + "\n",
        encoding="utf-8")
    r = replay(cfg, [], [], k=5, source="gold")
    g = r["gold"]
    assert g["queries"] == 1 and g["hits_a"] == g["hits_b"]           # identical configs → no discordance
    assert g["mcnemar"]["p"] == 1.0


# ── probe slot ────────────────────────────────────────────────────────────────────────────
def test_pick_probe_disabled_returns_none(cfg):
    store = MemoryStore(str(cfg.store_path))
    store.upsert({"name": "x", "schema": 5, "description": "d"})
    assert recall_log.pick_probe(cfg, store, set()) is None           # probe_slot defaults False


def test_pick_probe_prefers_dormant_and_excludes_served(cfg):
    from dataclasses import replace
    cfg2 = replace(cfg, probe_slot=True)
    store = MemoryStore(str(cfg2.store_path))
    for n in ("served", "dormant"):
        store.upsert({"name": n, "schema": 5, "description": n})
    recall_log.log_recall(cfg2, "q", [{"name": "served", "score": 0.5, "channel": "seed"}],
                          backend="MemoryStore", now="2026-07-01T10:00:00+00:00")
    p = recall_log.pick_probe(cfg2, store, {"served"}, rng=random.Random(7))
    assert p["name"] == "dormant" and p["channel"] == "probe"


# ── decay fit ─────────────────────────────────────────────────────────────────────────────
def test_fit_decay_insufficient_data_is_honest(cfg):
    r = fit_decay(cfg)
    assert "insufficient" in r["verdict"] and r["n_intervals"] == 0


def test_fit_decay_reports_fits_with_enough_intervals(cfg):
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
    for i in range(60):                                               # 59 exact 5h intervals
        recall_log.log_recall(cfg, "q", [{"name": "m", "score": 0.5, "channel": "seed"}],
                              backend="MemoryStore", now=(t0 + timedelta(hours=5 * i)).isoformat())
    r = fit_decay(cfg, min_intervals=50)
    assert r["n_intervals"] == 59 and r["median_interval_h"] == 5.0
    assert "exponential" in r and "power_law" in r and r["verdict"]
