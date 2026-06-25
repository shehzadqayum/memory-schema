"""Tests for the E1/E2/E3 evaluation-weakness fixes.

E1 — Neo4j list_all() now returns relations/associations (observability).
E2 — salience eval measures a heuristic classifier (not just baseline/perfect).
E3 — retrieval score-blend weights are configurable via MemoryConfig.
"""

from unittest.mock import patch, MagicMock

from memoryschema.config import MemoryConfig
from memoryschema.store import MemoryStore, _resolve_weights


# --- E3: configurable weights ---

class TestResolveWeights:
    def test_defaults_without_config(self):
        assert _resolve_weights(None, 'semantic') == (0.2, 0.3, 0.5)
        assert _resolve_weights(None, 'structured') == (0.3, 0.5, 0.2)

    def test_config_default_fields_match_legacy(self):
        cfg = MemoryConfig()
        assert _resolve_weights(cfg, 'semantic') == (0.2, 0.3, 0.5)
        assert _resolve_weights(cfg, 'structured') == (0.3, 0.5, 0.2)

    def test_config_override_applied(self):
        cfg = MemoryConfig(semantic_weights=(0.1, 0.1, 0.8))
        assert _resolve_weights(cfg, 'semantic') == (0.1, 0.1, 0.8)

    def test_unknown_mode_falls_back_to_semantic(self):
        assert _resolve_weights(None, 'mystery') == (0.2, 0.3, 0.5)

    def test_malformed_weights_fall_back(self):
        cfg = MemoryConfig(semantic_weights=(0.5, 0.5))  # wrong length
        assert _resolve_weights(cfg, 'semantic') == (0.2, 0.3, 0.5)


class TestConfigurableWeightsScoring:
    def test_importance_vs_relevance_weighting(self, tmp_path):
        # High importance, zero relevance. Importance-heavy weights should
        # score it higher than relevance-heavy weights.
        entry = {'name': 'x', 'type': 'episodic', 'importance': 10}
        imp_cfg = MemoryConfig(semantic_weights=(0.0, 1.0, 0.0))
        rel_cfg = MemoryConfig(semantic_weights=(0.0, 0.0, 1.0))
        s_imp = MemoryStore(str(tmp_path / 'a.jsonl'), config=imp_cfg)._score_entry(
            entry, precomputed_relevance=0.0)
        s_rel = MemoryStore(str(tmp_path / 'b.jsonl'), config=rel_cfg)._score_entry(
            entry, precomputed_relevance=0.0)
        assert s_imp > s_rel

    def test_no_config_still_scores(self, tmp_path):
        store = MemoryStore(str(tmp_path / 'c.jsonl'))  # config=None
        score = store._score_entry({'name': 'x', 'importance': 5})
        assert 0.0 <= score <= 1.0


# --- E2: salience heuristic classifier ---

class TestSalienceScorer:
    def test_write_cue(self):
        from memoryschema.eval.salience_scorer import classify_salience
        assert classify_salience(
            "We decided to use PostgreSQL because of concurrency") == 'write'

    def test_decline_cue(self):
        from memoryschema.eval.salience_scorer import classify_salience
        assert classify_salience("Running pytest... 45 passed in 2.3s") == 'decline'

    def test_empty_defaults_to_decline(self):
        from memoryschema.eval.salience_scorer import classify_salience
        assert classify_salience("") == 'decline'

    def test_beats_baseline_on_fixtures(self):
        from memoryschema.eval.salience_scorer import classify_salience
        from memoryschema.eval.fixtures import build_salience_fixtures
        from memoryschema.eval.metrics import evaluate_salience
        fixtures = build_salience_fixtures()
        system = [{'excerpt': f['excerpt'],
                   'decision': classify_salience(f['excerpt'])} for f in fixtures]
        res = evaluate_salience(system, fixtures)
        # Must be a real measurement that beats the all-write baseline (f1≈0.667).
        assert res['f1'] > 0.667
        assert res['accuracy'] > 0.5


# --- E1: Neo4j list_all returns relations/associations ---

def _mock_neo4j_store(record):
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    session.run.return_value = [record]
    return driver, session


class TestListAllIncludesGraph:
    def test_list_all_returns_associations_and_relations(self):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        record = {
            'm': {'name': 'a', 'type': 'semantic'},
            'relations': [{'target': 'b', 'type': 'USES'}],
            'backlinks': [{'source': 'z', 'type': 'INFORMS'}],
            'associations': [{'name': 'c', 'score': 0.9}],
        }
        driver, session = _mock_neo4j_store(record)
        with patch("memoryschema.neo4j_store.GraphDatabase") as gd:
            gd.driver.return_value = driver
            store = Neo4jMemoryStore(uri="bolt://x", user="u", password="p")
            results = store.list_all()
        assert results[0]['associations'] == [{'name': 'c', 'score': 0.9}]
        assert results[0]['relations'] == [{'target': 'b', 'type': 'USES'}]
        assert results[0]['backlinks'] == [{'source': 'z', 'type': 'INFORMS'}]
