"""Tests for field-level embedding spaces (M1.1 + M1.2).

Covers:
- compose_embedding_text for observations and reasoning spaces
- Registry contains all three spaces
- Combiner handles multi-space inputs
- Empty field returns empty string (structural absence)
- Multi-space scoring in MemoryStore (_score_entry, _score_all_entries)
- Backward compat: entries with only `embedding` field
"""

import json
import pytest
from memoryschema.embedding_input import compose_embedding_text
from memoryschema.spaces import (
    get_registry, get_space, combine_similarities, EXPERIMENT_WEIGHTS,
)
from memoryschema.store import MemoryStore, _cosine_similarity


# --- Embedding input composition ---

def _make_entry(**overrides):
    base = {
        'name': 'test-entry',
        'description': 'Test description',
        'observations': ['Fact A', 'Fact B'],
        'prompt': 'What is the test?',
        'reasoning': 'Because we need to verify behavior.',
    }
    base.update(overrides)
    return base


class TestObservationsSpace:
    def test_observations_only(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='observations')
        assert 'Fact A' in text
        assert 'Fact B' in text
        assert 'description' not in text.lower()
        assert 'verify behavior' not in text

    def test_empty_observations_returns_empty(self):
        entry = _make_entry(observations=[])
        assert compose_embedding_text(entry, space='observations') == ''

    def test_no_observations_key_returns_empty(self):
        entry = {'name': 'no-obs', 'description': 'No observations'}
        assert compose_embedding_text(entry, space='observations') == ''

    def test_max_chars_truncation(self):
        entry = _make_entry(observations=['x' * 100])
        text = compose_embedding_text(entry, space='observations', max_chars=50)
        assert len(text) <= 50


class TestReasoningSpace:
    def test_reasoning_only(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='reasoning')
        assert 'verify behavior' in text
        assert 'What is the test' not in text  # prompt is NOT in reasoning space
        assert 'Fact A' not in text
        assert 'description' not in text.lower()

    def test_reasoning_text_exact(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='reasoning')
        assert text == 'Because we need to verify behavior.'

    def test_no_reasoning_returns_empty(self):
        entry = _make_entry(reasoning=None)
        text = compose_embedding_text(entry, space='reasoning')
        assert text == ''

    def test_empty_reasoning_and_prompt_returns_empty(self):
        entry = _make_entry(reasoning=None, prompt=None)
        assert compose_embedding_text(entry, space='reasoning') == ''

    def test_no_reasoning_key_returns_empty(self):
        entry = {'name': 'no-reason', 'description': 'No reasoning'}
        assert compose_embedding_text(entry, space='reasoning') == ''

    def test_max_chars_truncation(self):
        entry = _make_entry(reasoning='x' * 100)
        text = compose_embedding_text(entry, space='reasoning', max_chars=50)
        assert len(text) <= 50


class TestDefaultSpaceUnchanged:
    def test_default_includes_all_fields(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='default')
        assert 'test-entry' in text
        assert 'Test description' in text
        assert 'Fact A' in text
        assert 'What is the test' in text
        assert 'verify behavior' in text

    def test_unknown_space_raises(self):
        with pytest.raises(ValueError, match='Unknown embedding space'):
            compose_embedding_text(_make_entry(), space='nonexistent')


class TestNameSpace:
    def test_name_only(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='name')
        assert text == 'test-entry'
        assert 'description' not in text.lower()
        assert 'Fact A' not in text

    def test_empty_name_returns_empty(self):
        entry = {'description': 'No name'}
        assert compose_embedding_text(entry, space='name') == ''

    def test_max_chars_truncation(self):
        entry = _make_entry()
        entry['name'] = 'x' * 200
        text = compose_embedding_text(entry, space='name', max_chars=50)
        assert len(text) <= 50


class TestPromptSpace:
    def test_prompt_only(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='prompt')
        assert text == 'What is the test?'
        assert 'Fact A' not in text
        assert 'verify behavior' not in text
        assert 'description' not in text.lower()

    def test_empty_prompt_returns_empty(self):
        entry = _make_entry(prompt=None)
        assert compose_embedding_text(entry, space='prompt') == ''

    def test_no_prompt_key_returns_empty(self):
        entry = {'name': 'no-prompt', 'description': 'No prompt'}
        assert compose_embedding_text(entry, space='prompt') == ''

    def test_max_chars_truncation(self):
        entry = _make_entry(prompt='x' * 200)
        text = compose_embedding_text(entry, space='prompt', max_chars=50)
        assert len(text) <= 50


class TestDescriptionSpace:
    def test_description_only(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='description')
        assert text == 'Test description'
        assert 'Fact A' not in text
        assert 'verify behavior' not in text

    def test_empty_description_returns_empty(self):
        entry = _make_entry(description='')
        assert compose_embedding_text(entry, space='description') == ''

    def test_no_description_key_returns_empty(self):
        entry = {'name': 'no-desc', 'observations': ['fact']}
        assert compose_embedding_text(entry, space='description') == ''

    def test_max_chars_truncation(self):
        entry = _make_entry(description='x' * 200)
        text = compose_embedding_text(entry, space='description', max_chars=50)
        assert len(text) <= 50


# --- Registry ---

class TestRegistry:
    def test_registry_has_six_spaces(self):
        reg = get_registry()
        assert set(reg.keys()) == {'default', 'name', 'description', 'observations', 'prompt', 'reasoning'}

    def test_all_spaces_immutable(self):
        for name, space in get_registry().items():
            assert space.space_type == 'immutable', f'{name} should be immutable'

    def test_all_spaces_use_voyage(self):
        for name, space in get_registry().items():
            assert space.embedder == 'voyage', f'{name} should use voyage'

    def test_space_compose_input(self):
        entry = _make_entry()
        obs_space = get_space('observations')
        text = obs_space.compose_input(entry)
        assert 'Fact A' in text
        assert 'description' not in text.lower()

    def test_get_space_returns_none_for_unknown(self):
        assert get_space('nonexistent') is None


# --- Combiner with multi-space ---

class TestCombinerMultiSpace:
    def test_single_default_identity(self):
        assert combine_similarities({'default': 0.8}) == 0.8

    def test_three_spaces_equal_weight(self):
        sims = {'default': 0.9, 'observations': 0.6, 'reasoning': 0.3}
        result = combine_similarities(sims)
        assert abs(result - 0.6) < 1e-9

    def test_two_spaces_coverage_aware(self):
        sims = {'default': 0.8, 'observations': 0.4}
        result = combine_similarities(sims)
        assert abs(result - 0.6) < 1e-9

    def test_absent_space_not_counted(self):
        """Entry without reasoning → only default + observations contribute."""
        sims = {'default': 0.9, 'observations': 0.6}
        result = combine_similarities(sims)
        # Average of 0.9 and 0.6 = 0.75, NOT (0.9+0.6+0)/3
        assert abs(result - 0.75) < 1e-9

    def test_empty_sims_returns_zero(self):
        assert combine_similarities({}) == 0.0

    def test_weighted_combiner(self):
        sims = {'default': 0.9, 'observations': 0.6, 'reasoning': 0.3}
        weights = {'default': 1.0, 'observations': 1.0, 'reasoning': 1.0}
        result = combine_similarities(sims, weights=weights)
        assert abs(result - 0.6) < 1e-9


# --- Multi-space scoring in MemoryStore (M1.2) ---

# Helper: unit vectors for deterministic scoring tests
_VEC_A = [1.0, 0.0, 0.0]
_VEC_B = [0.0, 1.0, 0.0]
_VEC_C = [0.0, 0.0, 1.0]
_VEC_AB = [0.7071, 0.7071, 0.0]  # ~45 degrees between A and B


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / 'test.jsonl'))


class TestMultiSpaceRelevance:
    """Tests for _multi_space_relevance static method."""

    def test_multi_space_three_spaces(self):
        entry = {
            'name': 'test',
            'embeddings': {
                'default': _VEC_A,
                'observations': _VEC_A,
                'reasoning': _VEC_B,
            },
        }
        # Query aligned with A → default=1.0, observations=1.0, reasoning=0.0
        rel = MemoryStore._multi_space_relevance(entry, _VEC_A)
        expected = (1.0 + 1.0 + 0.0) / 3
        assert abs(rel - expected) < 0.01

    def test_legacy_embedding_backward_compat(self):
        """Entry with only `embedding` field uses it as default space."""
        entry = {'name': 'legacy', 'embedding': _VEC_A}
        rel = MemoryStore._multi_space_relevance(entry, _VEC_A)
        assert abs(rel - 1.0) < 0.01

    def test_embeddings_dict_takes_precedence(self):
        """Entry with both `embeddings` and `embedding` uses the dict."""
        entry = {
            'name': 'both',
            'embedding': _VEC_A,  # legacy, should be ignored
            'embeddings': {'default': _VEC_B},  # should be used
        }
        # Query aligned with A → default (B) gives 0.0
        rel = MemoryStore._multi_space_relevance(entry, _VEC_A)
        assert abs(rel - 0.0) < 0.01

    def test_structural_absence(self):
        """Entry missing a space → combiner averages only present spaces."""
        entry = {
            'name': 'partial',
            'embeddings': {
                'default': _VEC_A,
                'observations': _VEC_A,
                # No 'reasoning' — structural absence
            },
        }
        rel = MemoryStore._multi_space_relevance(entry, _VEC_A)
        # Both present spaces have sim=1.0 → average = 1.0
        assert abs(rel - 1.0) < 0.01

    def test_no_embeddings_returns_zero(self):
        entry = {'name': 'bare'}
        rel = MemoryStore._multi_space_relevance(entry, _VEC_A)
        assert rel == 0.0


class TestScoreEntryMultiSpace:
    """Tests for _score_entry with multi-space embeddings."""

    def test_multi_space_higher_than_no_embedding(self, store):
        with_emb = {
            'name': 'has-emb', 'importance': 5,
            'embeddings': {'default': _VEC_A},
        }
        no_emb = {'name': 'no-emb', 'importance': 5}
        score_with = store._score_entry(with_emb, query_embedding=_VEC_A)
        score_without = store._score_entry(no_emb, query_embedding=_VEC_A)
        assert score_with > score_without

    def test_precomputed_still_works(self, store):
        entry = {'name': 'test', 'importance': 5}
        score = store._score_entry(entry, precomputed_relevance=0.9)
        assert score > 0

    def test_legacy_embedding_scores(self, store):
        entry = {'name': 'legacy', 'importance': 5, 'embedding': _VEC_A}
        score = store._score_entry(entry, query_embedding=_VEC_A)
        assert score > 0


class TestScoreAllEntriesMultiSpace:
    """Tests for _score_all_entries numpy path with multi-space."""

    def test_mixed_entries(self, store):
        entries = [
            {'name': 'multi', 'importance': 5,
             'embeddings': {'default': _VEC_A, 'observations': _VEC_A}},
            {'name': 'legacy', 'importance': 5, 'embedding': _VEC_A},
            {'name': 'bare', 'importance': 5},
        ]
        scored = store._score_all_entries(entries, 'test', _VEC_A)
        assert len(scored) == 3
        names = {e['name'] for e, _ in scored}
        assert names == {'multi', 'legacy', 'bare'}

    def test_multi_space_entries_scored(self, store):
        entries = [
            {'name': 'aligned', 'importance': 5,
             'embeddings': {'default': _VEC_A, 'observations': _VEC_A}},
            {'name': 'orthogonal', 'importance': 5,
             'embeddings': {'default': _VEC_B, 'observations': _VEC_B}},
        ]
        scored = store._score_all_entries(entries, 'test', _VEC_A)
        scores = {e['name']: s for e, s in scored}
        assert scores['aligned'] > scores['orthogonal']

    def test_embeddings_dict_persisted_in_jsonl(self, store):
        """Verify embeddings dict round-trips through JSONL serialization."""
        entry = {
            'name': 'persist-test', 'schema': 4,
            'description': 'Test persistence',
            'embedding': _VEC_A,
            'embeddings': {
                'default': _VEC_A,
                'observations': _VEC_B,
                'reasoning': _VEC_C,
            },
        }
        store.upsert(entry)
        loaded = store.get('persist-test')
        assert loaded['embeddings']['default'] == _VEC_A
        assert loaded['embeddings']['observations'] == _VEC_B
        assert loaded['embeddings']['reasoning'] == _VEC_C
        assert loaded['embedding'] == _VEC_A


# --- M1.4: Experiment combiner configuration ---

class TestExperimentCombiner:
    """Verify the M1 experiment configuration: equal weighting, no query-type
    classification, coverage-aware. These tests exercise the full scoring path
    to confirm the combiner is wired correctly."""

    def test_experiment_weights_is_none(self):
        """M1 experiment uses equal weighting (None = coverage-aware average)."""
        assert EXPERIMENT_WEIGHTS is None

    def test_three_space_equal_weight_through_scoring(self, store):
        """Full path: entry with 3 spaces → combiner averages all 3."""
        entry = {
            'name': 'three-space', 'importance': 5,
            'embeddings': {
                'default': _VEC_A,
                'observations': _VEC_A,
                'reasoning': _VEC_B,
            },
        }
        # With query aligned to A: default=1.0, obs=1.0, reasoning=0.0
        # Equal weight: (1.0 + 1.0 + 0.0) / 3 ≈ 0.667
        score_3 = store._score_entry(entry, query_embedding=_VEC_A)

        # Same entry with only default space
        entry_1 = {
            'name': 'one-space', 'importance': 5,
            'embeddings': {'default': _VEC_A},
        }
        # With query aligned to A: default=1.0 (identity)
        score_1 = store._score_entry(entry_1, query_embedding=_VEC_A)

        # Three-space score should be lower because reasoning drags it down
        assert score_3 < score_1

    def test_structural_absence_does_not_penalize(self, store):
        """Entry missing reasoning → combiner averages 2 spaces, not 3 with zero."""
        entry_2 = {
            'name': 'two-space', 'importance': 5,
            'embeddings': {
                'default': _VEC_A,
                'observations': _VEC_A,
                # No reasoning — structural absence
            },
        }
        # Both present spaces have sim=1.0 → combined = 1.0
        # NOT (1.0 + 1.0 + 0.0) / 3
        entry_3_all_aligned = {
            'name': 'three-aligned', 'importance': 5,
            'embeddings': {
                'default': _VEC_A,
                'observations': _VEC_A,
                'reasoning': _VEC_A,
            },
        }
        score_2 = store._score_entry(entry_2, query_embedding=_VEC_A)
        score_3 = store._score_entry(entry_3_all_aligned, query_embedding=_VEC_A)
        # Both should be identical — all present spaces have sim=1.0
        assert abs(score_2 - score_3) < 0.01

    def test_field_disagreement_detectable(self):
        """Cross-space disagreement is observable from per-space sims."""
        entry = {
            'name': 'disagree',
            'embeddings': {
                'default': _VEC_AB,
                'observations': _VEC_A,
                'reasoning': _VEC_B,
            },
        }
        query = _VEC_A  # aligned with observations, orthogonal to reasoning
        rel = MemoryStore._multi_space_relevance(entry, query)

        # Compute per-space sims directly
        sim_obs = _cosine_similarity(query, _VEC_A)   # ≈ 1.0
        sim_rea = _cosine_similarity(query, _VEC_B)   # ≈ 0.0
        disagreement = abs(sim_obs - sim_rea)

        assert disagreement > 0.9  # High disagreement is detectable
        # Combined score is the average
        sim_def = _cosine_similarity(query, _VEC_AB)
        expected = (max(0, sim_def) + max(0, sim_obs) + max(0, sim_rea)) / 3
        assert abs(rel - expected) < 0.02
