"""Tests for contradiction-aware reflect (Phase 5)."""

import json

import pytest

from memoryschema.store import MemoryStore
from memoryschema.tags import Observation
from memoryschema.consolidation import reflect, _check_cluster_contradictions


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "reflect.jsonl"))


def _make_episodic(store, name, description, observations=None, relations=None,
                   associations=None, embedding=None):
    """Helper to create an episodic entry with associations for clustering."""
    entry = {
        'name': name, 'schema': 4, 'type': 'episodic', 'description': description,
        'importance': 5, 'observations': observations or [],
    }
    if relations:
        entry['relations'] = relations
    if associations:
        entry['associations'] = associations
    if embedding:
        entry['embedding'] = embedding
    store.upsert(entry)


class TestCheckClusterContradictions:
    def test_clean_cluster(self):
        """No contradictions → empty reasons."""
        cluster = [
            {'name': 'a', 'description': 'First event', 'observations': [], 'relations': [], 'backlinks': []},
            {'name': 'b', 'description': 'Second event', 'observations': [], 'relations': [], 'backlinks': []},
        ]
        assert _check_cluster_contradictions(cluster) == []

    def test_contradicts_relation_detected(self):
        """CONTRADICTS relation between members → reasons."""
        cluster = [
            {'name': 'a', 'description': 'Claim A', 'observations': [],
             'relations': [{'target': 'b', 'type': 'CONTRADICTS'}], 'backlinks': []},
            {'name': 'b', 'description': 'Claim B', 'observations': [],
             'relations': [], 'backlinks': []},
        ]
        reasons = _check_cluster_contradictions(cluster)
        assert len(reasons) >= 1
        assert 'CONTRADICTS' in reasons[0]

    def test_numeric_contradiction_detected(self):
        """Different numeric claims for same unit → reasons."""
        cluster = [
            {'name': 'a', 'description': '472 tests passing', 'observations': [],
             'relations': [], 'backlinks': []},
            {'name': 'b', 'description': '433 tests passing', 'observations': [],
             'relations': [], 'backlinks': []},
        ]
        reasons = _check_cluster_contradictions(cluster)
        assert len(reasons) >= 1
        assert 'numeric-contradiction' in reasons[0]


class TestReflectSkip:
    def test_contradictory_cluster_skipped(self, store):
        """Cluster with CONTRADICTS relation is skipped by default."""
        _make_episodic(store, 'ev-1', 'Event 1',
                       associations=[{'name': 'ev-2', 'score': 0.9}])
        _make_episodic(store, 'ev-2', 'Event 2',
                       relations=[{'target': 'ev-1', 'type': 'CONTRADICTS'}],
                       associations=[{'name': 'ev-1', 'score': 0.9}])
        store.compute_backlinks()

        result = reflect(store, min_cluster=2)
        assert result['skipped'] >= 1
        assert result['summaries'] == 0

        # Members remain active (status defaults to 'active' when absent)
        assert store.get('ev-1').get('status', 'active') == 'active'
        assert store.get('ev-2').get('status', 'active') == 'active'

    def test_clean_cluster_synthesized(self, store):
        """Clean cluster synthesizes normally (regression guard)."""
        _make_episodic(store, 'clean-1', 'Clean event 1',
                       associations=[{'name': 'clean-2', 'score': 0.9}])
        _make_episodic(store, 'clean-2', 'Clean event 2',
                       associations=[{'name': 'clean-1', 'score': 0.9}])

        result = reflect(store, min_cluster=2)
        assert result['summaries'] >= 1
        assert result['skipped'] == 0


class TestIncludeContradictory:
    def test_flag_synthesizes_with_degraded_authority(self, store):
        """--include-contradictory: min importance, CONTRADICTS edges, inferred basis."""
        _make_episodic(store, 'c-1', 'Conflicting event 1',
                       observations=[Observation('472 tests passing')],
                       associations=[{'name': 'c-2', 'score': 0.9}])
        _make_episodic(store, 'c-2', 'Conflicting event 2',
                       observations=[Observation('433 tests passing')],
                       associations=[{'name': 'c-1', 'score': 0.9}])

        result = reflect(store, min_cluster=2, include_contradictory=True)
        assert result['summaries'] >= 1
        assert result['skipped'] == 0

        # Find the summary
        all_entries = store.list_all(include_inactive=True)
        summaries = [e for e in all_entries if e['name'].startswith('summary-')]
        assert len(summaries) >= 1
        summary = summaries[0]

        # Min importance (both have 5 → min is 5)
        assert summary['importance'] == 5

        # CONTRADICTS edges present
        contradicts_rels = [r for r in summary.get('relations', [])
                           if r.get('type') == 'CONTRADICTS']
        assert len(contradicts_rels) >= 1

        # Observations labelled inferred
        for obs in summary.get('observations', []):
            if isinstance(obs, Observation) and obs.basis is not None:
                assert obs.basis == 'inferred'


class TestReflectAudit:
    def test_skip_audit_record(self, store):
        """Skipped cluster produces a reflect_skip audit record."""
        _make_episodic(store, 'sk-1', 'Skip event 1',
                       relations=[{'target': 'sk-2', 'type': 'CONTRADICTS'}],
                       associations=[{'name': 'sk-2', 'score': 0.9}])
        _make_episodic(store, 'sk-2', 'Skip event 2',
                       associations=[{'name': 'sk-1', 'score': 0.9}])
        store.compute_backlinks()

        reflect(store, min_cluster=2)

        with open(store._audit_path) as f:
            records = [json.loads(line) for line in f]
        skip_records = [r for r in records if r.get('operation') == 'reflect_skip']
        assert len(skip_records) >= 1
        assert 'members' in skip_records[0].get('changes', {})
        assert 'reasons' in skip_records[0].get('changes', {})
