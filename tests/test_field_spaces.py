"""Tests for field-level embedding spaces (M1.1).

Covers:
- compose_embedding_text for observations and reasoning spaces
- Registry contains all three spaces
- Combiner handles multi-space inputs
- Empty field returns empty string (structural absence)
"""

import pytest
from memoryschema.embedding_input import compose_embedding_text
from memoryschema.spaces import get_registry, get_space, combine_similarities


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
    def test_reasoning_and_prompt(self):
        entry = _make_entry()
        text = compose_embedding_text(entry, space='reasoning')
        assert 'verify behavior' in text
        assert 'What is the test' in text
        assert 'Fact A' not in text
        assert 'description' not in text.lower()

    def test_reasoning_only_no_prompt(self):
        entry = _make_entry(prompt=None)
        text = compose_embedding_text(entry, space='reasoning')
        assert 'verify behavior' in text
        assert text == 'Because we need to verify behavior.'

    def test_prompt_only_no_reasoning(self):
        entry = _make_entry(reasoning=None)
        text = compose_embedding_text(entry, space='reasoning')
        assert 'What is the test' in text

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


# --- Registry ---

class TestRegistry:
    def test_registry_has_three_spaces(self):
        reg = get_registry()
        assert set(reg.keys()) == {'default', 'observations', 'reasoning'}

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
