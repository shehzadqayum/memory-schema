"""Evaluation harness tests.

Tests the fixture store, metrics computation, and poisoning defenses.
"""

import pytest

from memoryschema.store import MemoryStore
from tests.eval.fixtures import (
    build_fixture_entries,
    build_query_set,
    build_poisoning_entries,
)
from tests.eval.metrics import recall_at_k, mrr, ndcg_at_k, evaluate_all


@pytest.fixture
def eval_store(tmp_path):
    """Build a store populated with fixture entries."""
    store = MemoryStore(str(tmp_path / 'eval.jsonl'))
    for entry in build_fixture_entries():
        store.upsert(entry)
    return store


class TestMetrics:
    def test_recall_at_k_perfect(self):
        assert recall_at_k(['a', 'b', 'c'], ['a', 'b'], k=5) == 1.0

    def test_recall_at_k_partial(self):
        assert recall_at_k(['a', 'x', 'y'], ['a', 'b'], k=5) == 0.5

    def test_recall_at_k_empty_relevant(self):
        assert recall_at_k(['a', 'b'], [], k=5) == 1.0

    def test_recall_at_k_none_found(self):
        assert recall_at_k(['x', 'y', 'z'], ['a', 'b'], k=3) == 0.0

    def test_mrr_first(self):
        assert mrr(['a', 'b', 'c'], ['a']) == 1.0

    def test_mrr_second(self):
        assert mrr(['x', 'a', 'c'], ['a']) == 0.5

    def test_mrr_not_found(self):
        assert mrr(['x', 'y', 'z'], ['a']) == 0.0

    def test_ndcg_perfect(self):
        result = ndcg_at_k(['a', 'b', 'c'], ['a', 'b', 'c'], k=3)
        assert result == pytest.approx(1.0)

    def test_ndcg_empty_relevant(self):
        assert ndcg_at_k(['a', 'b'], [], k=5) == 1.0


class TestFixtureStore:
    def test_fixture_count(self, eval_store):
        entries = eval_store.list_all(include_inactive=True)
        assert len(entries) == 50  # 10+10+8+5+10+3+4

    def test_superseded_excluded(self, eval_store):
        results = eval_store.search(query='outdated')
        names = {r['name'] for r in results}
        for i in range(4):
            assert f'outdated-{i}' not in names

    def test_types_present(self, eval_store):
        entries = eval_store.list_all(include_inactive=True)
        types = {e.get('type') for e in entries}
        assert types == {'semantic', 'episodic', 'procedural'}

    def test_provenances_present(self, eval_store):
        entries = eval_store.list_all(include_inactive=True)
        provs = {e.get('provenance') for e in entries}
        assert provs == {'first-party', 'user', 'ingested', 'derived'}

    def test_hierarchy_levels(self, eval_store):
        entries = eval_store.list_all(include_inactive=True)
        projects = {e.get('project') for e in entries}
        assert 'org' in projects
        assert 'org.team' in projects
        assert 'org.team.sub' in projects


class TestPoisoningDefense:
    @pytest.fixture
    def poisoned_store(self, tmp_path):
        store = MemoryStore(str(tmp_path / 'poison.jsonl'))
        for entry in build_fixture_entries():
            store.upsert(entry)
        for entry in build_poisoning_entries():
            store.upsert(entry)
        return store

    def test_poison_entries_exist(self, poisoned_store):
        p1 = poisoned_store.get('poison-instruction-1')
        assert p1 is not None
        assert p1['provenance'] == 'ingested'

    def test_poison_marked_untrusted_in_recall(self, poisoned_store):
        results = poisoned_store.recall(query='system instruction')
        poison_results = [r for r in results if r['name'].startswith('poison-')]
        for r in poison_results:
            assert r.get('untrusted') is True

    def test_poison_ranks_below_first_party(self, poisoned_store):
        results = poisoned_store.recall(query='system architecture')
        if len(results) >= 2:
            first_party = [r for r in results if r.get('provenance') != 'ingested']
            ingested = [r for r in results if r.get('provenance') == 'ingested']
            if first_party and ingested:
                assert first_party[0]['score'] >= ingested[0]['score']


class TestEvaluateAll:
    def test_evaluate_runs(self, eval_store):
        query_set = build_query_set()
        result = evaluate_all(eval_store, query_set)
        assert 'queries' in result
        assert 'averages' in result
        assert len(result['queries']) == len(query_set)
        assert 'recall@5' in result['averages']
        assert 'mrr' in result['averages']
        assert 'ndcg@10' in result['averages']

    def test_superseded_query_excluded(self, eval_store):
        # The "outdated fact" query expects no relevant results
        # (superseded entries excluded from default recall)
        results = eval_store.recall(query='outdated fact')
        outdated = [r for r in results if r['name'].startswith('outdated-')]
        assert len(outdated) == 0


# --- Salience evaluation ---

class TestSalienceFixtures:
    def test_fixtures_exist(self):
        from tests.eval.fixtures import build_salience_fixtures
        fixtures = build_salience_fixtures()
        assert len(fixtures) >= 20

    def test_fixtures_balanced(self):
        from tests.eval.fixtures import build_salience_fixtures
        fixtures = build_salience_fixtures()
        writes = sum(1 for f in fixtures if f['decision'] == 'write')
        declines = sum(1 for f in fixtures if f['decision'] == 'decline')
        assert writes >= 8
        assert declines >= 8

    def test_fixture_structure(self):
        from tests.eval.fixtures import build_salience_fixtures
        for f in build_salience_fixtures():
            assert 'excerpt' in f
            assert 'decision' in f
            assert f['decision'] in ('write', 'decline')
            assert 'reason' in f


class TestSalienceMetrics:
    def test_perfect_score(self):
        from tests.eval.fixtures import build_salience_fixtures
        from tests.eval.metrics import evaluate_salience
        fixtures = build_salience_fixtures()
        perfect = [{'excerpt': f['excerpt'], 'decision': f['decision']} for f in fixtures]
        result = evaluate_salience(perfect, fixtures)
        assert result['precision'] == 1.0
        assert result['recall'] == 1.0
        assert result['f1'] == 1.0
        assert result['correct'] == result['total']

    def test_all_write_baseline(self):
        from tests.eval.fixtures import build_salience_fixtures
        from tests.eval.metrics import evaluate_salience
        fixtures = build_salience_fixtures()
        all_write = [{'excerpt': f['excerpt'], 'decision': 'write'} for f in fixtures]
        result = evaluate_salience(all_write, fixtures)
        assert result['recall'] == 1.0  # catches all writes
        assert result['precision'] < 1.0  # but also catches declines
        assert result['total'] == len(fixtures)

    def test_all_decline_baseline(self):
        from tests.eval.fixtures import build_salience_fixtures
        from tests.eval.metrics import evaluate_salience
        fixtures = build_salience_fixtures()
        all_decline = [{'excerpt': f['excerpt'], 'decision': 'decline'} for f in fixtures]
        result = evaluate_salience(all_decline, fixtures)
        assert result['recall'] == 0.0  # catches no writes
        assert result['precision'] == 0.0  # no predicted writes
