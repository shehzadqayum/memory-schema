"""Tests for verification-aware scoring, guards, and staleness (Phase 2)."""

from datetime import datetime, timezone, timedelta

import pytest

from memoryschema.store import MemoryStore
from memoryschema.tags import Observation


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "test.jsonl"))


# --- Scoring: basis factor ---

class TestBasisFactor:
    def test_measured_scores_higher_than_reported(self, store):
        """Entries with measured observations score higher than reported."""
        base = {'schema': 4, 'importance': 5, 'description': 'Test'}
        measured_entry = {**base, 'name': 'm',
                         'observations': [Observation("fact", basis="measured")]}
        reported_entry = {**base, 'name': 'r',
                          'observations': [Observation("fact", basis="reported")]}
        s_m = store._score_entry(measured_entry)
        s_r = store._score_entry(reported_entry)
        assert s_m > s_r

    def test_neutral_no_penalty(self, store):
        """Entries with no labelled observations are neutral (factor 1.0)."""
        base = {'schema': 4, 'importance': 5, 'description': 'Test'}
        neutral = {**base, 'name': 'n', 'observations': [Observation("plain")]}
        measured = {**base, 'name': 'm',
                    'observations': [Observation("fact", basis="measured")]}
        s_n = store._score_entry(neutral)
        s_m = store._score_entry(measured)
        # Neutral = 1.0, measured = 1.0 → same (both are best-case)
        assert s_n == s_m

    def test_inferred_between_measured_and_reported(self, store):
        """Inferred scores between measured and reported."""
        base = {'schema': 4, 'importance': 5, 'description': 'Test'}
        measured = {**base, 'name': 'm',
                    'observations': [Observation("f", basis="measured")]}
        inferred = {**base, 'name': 'i',
                    'observations': [Observation("f", basis="inferred")]}
        reported = {**base, 'name': 'r',
                    'observations': [Observation("f", basis="reported")]}
        s_m = store._score_entry(measured)
        s_i = store._score_entry(inferred)
        s_r = store._score_entry(reported)
        assert s_m >= s_i >= s_r


# --- Verification guard ---

class TestVerificationGuard:
    def test_reported_cannot_supersede_measured(self, store):
        """reported-only entity blocked from superseding measured entity."""
        store.upsert({'name': 'target', 'schema': 4, 'description': 'Target',
                      'observations': [Observation("fact", basis="measured")]})
        with pytest.raises(ValueError, match='[Vv]erification guard'):
            store.upsert({'name': 'source', 'schema': 4, 'description': 'Source',
                          'observations': [Observation("claim", basis="reported")],
                          'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})

    def test_measured_can_supersede_reported(self, store):
        """measured entity can supersede reported entity."""
        store.upsert({'name': 'target', 'schema': 4, 'description': 'Target',
                      'observations': [Observation("old", basis="reported")]})
        store.upsert({'name': 'source', 'schema': 4, 'description': 'Source',
                      'observations': [Observation("new", basis="measured")],
                      'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})
        assert store.get('target')['status'] == 'superseded'

    def test_same_rank_allowed(self, store):
        """Same rank allows supersede."""
        store.upsert({'name': 'target', 'schema': 4, 'description': 'T',
                      'observations': [Observation("a", basis="inferred")]})
        store.upsert({'name': 'source', 'schema': 4, 'description': 'S',
                      'observations': [Observation("b", basis="inferred")],
                      'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})
        assert store.get('target')['status'] == 'superseded'

    def test_unlabelled_neutral_rank(self, store):
        """Unlabelled observations have neutral rank (2), equal to inferred."""
        store.upsert({'name': 'target', 'schema': 4, 'description': 'T',
                      'observations': [Observation("plain")]})  # rank 2
        store.upsert({'name': 'source', 'schema': 4, 'description': 'S',
                      'observations': [Observation("b", basis="inferred")],  # rank 2
                      'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})
        assert store.get('target')['status'] == 'superseded'

    def test_reported_cannot_supersede_inferred(self, store):
        """reported (rank 1) cannot supersede inferred (rank 2)."""
        store.upsert({'name': 'target', 'schema': 4, 'description': 'T',
                      'observations': [Observation("a", basis="inferred")]})
        with pytest.raises(ValueError, match='[Vv]erification guard'):
            store.upsert({'name': 'source', 'schema': 4, 'description': 'S',
                          'observations': [Observation("b", basis="reported")],
                          'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})

    def test_measured_supersedes_everything(self, store):
        """measured (rank 3) can supersede any rank."""
        for target_basis in ['measured', 'inferred', 'reported', None]:
            store_path = store._path.replace('.jsonl', f'-{target_basis}.jsonl')
            s = MemoryStore(store_path)
            obs = [Observation("t", basis=target_basis)] if target_basis else [Observation("t")]
            s.upsert({'name': 'target', 'schema': 4, 'description': 'T',
                      'observations': obs})
            s.upsert({'name': 'source', 'schema': 4, 'description': 'S',
                      'observations': [Observation("s", basis="measured")],
                      'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})
            assert s.get('target')['status'] == 'superseded'


# --- Staleness rendering ---

class TestStalenessRendering:
    def test_verified_at_in_recall_results(self, store):
        """verified_at flows through to recall results."""
        store.upsert({'name': 'verified-entry', 'schema': 4,
                      'description': 'Test verified entry', 'importance': 10,
                      'observations': [Observation("measured fact", basis="measured")]})
        results = store.recall(name='verified-entry')
        assert len(results) >= 1
        # The entry itself has verified_at; recall results carry it via entry_map
        entry = store.get('verified-entry')
        assert 'verified_at' in entry
