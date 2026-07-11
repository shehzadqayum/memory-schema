"""The retrieval-scoring config knobs actually affect scoring (they used to be silent placebos).

`recency_decay` and `mitigation_dampening` were hardcoded in both stores' `_score_entry`; setting them in
`memoryschema.toml` did nothing. These pin that the config is now honoured, AND that `config=None` /
default-config reproduce the historical literals (0.995 / 0.95) — so no default behaviour changed.
"""
from datetime import datetime, timedelta, timezone

from memoryschema.config import MemoryConfig
from memoryschema.store import MemoryStore


def _old_episodic(hours):
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return {"name": "e", "type": "episodic", "importance": 5, "last_accessed": ts, "backlinks": []}


def test_recency_decay_config_is_honoured():
    entry = _old_episodic(100)
    hi = MemoryStore("x.jsonl", config=MemoryConfig(recency_decay=0.995))._score_entry(dict(entry))
    lo = MemoryStore("x.jsonl", config=MemoryConfig(recency_decay=0.5))._score_entry(dict(entry))
    assert lo < hi, f"a faster recency_decay must lower an old entry's score ({lo} !< {hi})"


def test_mitigation_dampening_config_is_honoured():
    entry = {"name": "e", "type": "semantic", "importance": 8,
             "backlinks": [{"type": "MITIGATES", "target": "x"}]}
    light = MemoryStore("x.jsonl", config=MemoryConfig(mitigation_dampening=0.95))._score_entry(dict(entry))
    heavy = MemoryStore("x.jsonl", config=MemoryConfig(mitigation_dampening=0.1))._score_entry(dict(entry))
    assert heavy < light, f"a stronger mitigation dampening must lower a mitigated entry's score ({heavy} !< {light})"


def test_defaults_unchanged_config_none_equals_default_config():
    entry = _old_episodic(50)
    entry["backlinks"] = [{"type": "MITIGATES", "target": "x"}]
    none_cfg = MemoryStore("x.jsonl", config=None)._score_entry(dict(entry))
    def_cfg = MemoryStore("x.jsonl", config=MemoryConfig())._score_entry(dict(entry))
    assert none_cfg == def_cfg, "config=None must score identically to the default config (0.995 / 0.95 literals)"
