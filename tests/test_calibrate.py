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


def test_probe_row_is_logged_even_past_the_top10_cap(cfg):
    # at --limit >= 10 the appended probe is the 11th row; the log must still carry it
    # (the probe's citation is the decensoring signal — an unlogged probe can't attribute)
    rows = [{"name": f"m{i}", "score": 0.5, "channel": "seed"} for i in range(10)]
    rows.append({"name": "the-probe", "score": 0.0, "channel": "probe"})
    recall_log.log_recall(cfg, "q", rows, backend="MemoryStore",
                          now="2026-07-01T10:00:00+00:00")
    ev = recall_log.read_events(cfg)[0]
    assert len(ev["hits"]) == 11
    assert ev["hits"][-1] == {"name": "the-probe", "score": 0.0, "channel": "probe"}


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


# ── A3: promoted params (seed_count, embed_max_chars) ───────────────────────────────────────
def test_seed_count_config_widens_the_seed_set(cfg):
    from dataclasses import replace
    from memoryschema.store import MemoryStore
    # 5 distinct entities; a name-less keyword recall seeds from the top-N scored
    cfg2 = replace(cfg, seed_count=5)
    store = MemoryStore(str(cfg2.store_path), config=cfg2)
    for i in range(5):
        store.upsert({"name": f"topic-{i}", "schema": 5, "description": f"shared topic term item {i}",
                      "observations": [f"shared topic term item {i}"]})
    res = store.recall(query="shared topic term", limit=20)
    seeds = [r["name"] for r in res if r.get("channel") == "seed"]
    assert len(seeds) == 5                                   # config.seed_count honoured (default would be 3)


def test_embed_max_chars_from_config_but_hash_is_invariant(cfg):
    from dataclasses import replace
    from memoryschema import spaces
    from memoryschema.embedding_input import embed_input_hash
    entry = {"name": "e", "description": "d" * 50, "observations": ["o" * 5000]}
    lens = []
    def capture(text):                                       # embed_fn: record the composed input length
        lens.append(len(text))
        return [0.1, 0.2, 0.3, 0.4]
    spaces.embed_all_spaces(entry, config=replace(cfg, embed_max_chars=200), embed_fn=capture)
    assert lens and max(lens) <= 200                         # config cap applied to the composed input
    # the provenance hash is over the UNTRUNCATED compose_full_text — invariant to the cap
    h_default = embed_input_hash(entry)
    spaces.embed_all_spaces(entry, config=replace(cfg, embed_max_chars=8000), embed_fn=capture)
    assert embed_input_hash(entry) == h_default


def test_embed_max_chars_default_matches_module_constant():
    # the two must stay in lockstep — a divergence would embed a different length than the docs claim
    from memoryschema.config import MemoryConfig
    from memoryschema.embedding_input import DEFAULT_MAX_CHARS
    assert MemoryConfig(project_root=".").embed_max_chars == DEFAULT_MAX_CHARS
