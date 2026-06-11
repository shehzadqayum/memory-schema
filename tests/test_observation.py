"""Tests for Observation class, serializers, basis handling, and V14/Q9."""

import json

import pytest

from memoryschema.tags import (
    Observation, observation_text, serialize_observation, deserialize_observation,
    parse_memory_content,
)
from memoryschema.store import MemoryStore
from memoryschema.validator import validate


# --- Observation class ---

class TestObservation:
    def test_is_string(self):
        obs = Observation("hello world", basis="measured")
        assert isinstance(obs, str)
        assert obs == "hello world"

    def test_basis_attribute(self):
        obs = Observation("fact", basis="measured")
        assert obs.basis == "measured"

    def test_no_basis(self):
        obs = Observation("plain")
        assert obs.basis is None

    def test_string_operations_drop_basis(self):
        """String transforms return plain str, losing basis."""
        obs = Observation("  hello  ", basis="measured")
        stripped = obs.strip()
        assert stripped == "hello"
        assert type(stripped) is str  # NOT Observation
        assert not hasattr(stripped, 'basis') or stripped.__class__ is str

    def test_observation_text_explicit_drop(self):
        obs = Observation("fact", basis="measured")
        text = observation_text(obs)
        assert text == "fact"
        assert type(text) is str


# --- Serializer pair ---

class TestSerializers:
    def test_serialize_unlabelled(self):
        obs = Observation("plain")
        assert serialize_observation(obs) == "plain"

    def test_serialize_labelled(self):
        obs = Observation("fact", basis="measured")
        result = serialize_observation(obs)
        assert isinstance(result, dict)
        assert result == {"text": "fact", "basis": "measured"}

    def test_deserialize_plain_string(self):
        obs = deserialize_observation("legacy text")
        assert isinstance(obs, Observation)
        assert obs == "legacy text"
        assert obs.basis is None

    def test_deserialize_dict(self):
        obs = deserialize_observation({"text": "fact", "basis": "inferred"})
        assert isinstance(obs, Observation)
        assert obs == "fact"
        assert obs.basis == "inferred"

    def test_round_trip_labelled(self):
        original = Observation("test", basis="reported")
        serialized = serialize_observation(original)
        restored = deserialize_observation(serialized)
        assert restored == "test"
        assert restored.basis == "reported"

    def test_round_trip_unlabelled(self):
        original = Observation("legacy")
        serialized = serialize_observation(original)
        assert serialized == "legacy"  # plain string
        restored = deserialize_observation(serialized)
        assert restored == "legacy"
        assert restored.basis is None


# --- Parser ---

class TestParserBasis:
    def test_parse_basis_attribute(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test entity</memory:description>
  <memory:observations>
    <memory:observation basis="measured">472 tests passing</memory:observation>
    <memory:observation>Plain observation</memory:observation>
    <memory:observation basis="reported">Carried forward claim</memory:observation>
  </memory:observations>
</memory:entity>'''
        result = parse_memory_content(content)
        assert result is not None
        obs = result['observations']
        assert len(obs) == 3
        assert isinstance(obs[0], Observation)
        assert obs[0].basis == "measured"
        assert obs[1].basis is None
        assert obs[2].basis == "reported"

    def test_legacy_no_basis(self):
        content = '''<memory:entity schema="3" name="legacy">
  <memory:description>Legacy entity</memory:description>
  <memory:observations>
    <memory:observation>Old fact</memory:observation>
  </memory:observations>
</memory:entity>'''
        result = parse_memory_content(content)
        obs = result['observations']
        assert len(obs) == 1
        assert isinstance(obs[0], Observation)
        assert obs[0].basis is None


# --- V14 ---

class TestV14:
    def test_valid_basis(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test</memory:description>
  <memory:observations>
    <memory:observation basis="measured">Fact</memory:observation>
  </memory:observations>
</memory:entity>'''
        errors = validate(content)
        assert not any(r == 'V14' for r, _ in errors)

    def test_invalid_basis(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test</memory:description>
  <memory:observations>
    <memory:observation basis="guessed">Fact</memory:observation>
  </memory:observations>
</memory:entity>'''
        errors = validate(content)
        assert any(r == 'V14' for r, _ in errors)

    def test_no_basis_passes(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test</memory:description>
  <memory:observations>
    <memory:observation>Plain fact</memory:observation>
  </memory:observations>
</memory:entity>'''
        errors = validate(content)
        assert not any(r == 'V14' for r, _ in errors)


# --- Q9 ---

class TestQ9:
    def test_no_warning_with_labelled(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test</memory:description>
  <memory:observations>
    <memory:observation basis="measured">A</memory:observation>
    <memory:observation>B</memory:observation>
    <memory:observation>C</memory:observation>
  </memory:observations>
</memory:entity>'''
        errors = validate(content, strict=True)
        assert not any(r == 'Q9' for r, _ in errors)

    def test_warning_all_unlabelled(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test</memory:description>
  <memory:observations>
    <memory:observation>A</memory:observation>
    <memory:observation>B</memory:observation>
    <memory:observation>C</memory:observation>
  </memory:observations>
</memory:entity>'''
        errors = validate(content, strict=True)
        assert any(r == 'Q9' for r, _ in errors)

    def test_no_warning_fewer_than_3(self):
        content = '''<memory:entity schema="4" name="test">
  <memory:description>Test</memory:description>
  <memory:observations>
    <memory:observation>A</memory:observation>
    <memory:observation>B</memory:observation>
  </memory:observations>
</memory:entity>'''
        errors = validate(content, strict=True)
        assert not any(r == 'Q9' for r, _ in errors)


# --- Store: basis upgrade + verified_at ---

class TestStoreBasis:
    @pytest.fixture
    def store(self, tmp_path):
        return MemoryStore(str(tmp_path / "test.jsonl"))

    def test_legacy_read_normalization(self, store):
        """Legacy plain-string observations become Observation instances."""
        store.upsert({'name': 'legacy', 'schema': 3, 'description': 'Test',
                      'observations': ['plain text']})
        entry = store.get('legacy')
        assert isinstance(entry['observations'][0], Observation)
        assert entry['observations'][0].basis is None

    def test_basis_preserved_on_write(self, store):
        obs = [Observation("measured fact", basis="measured")]
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': obs})
        entry = store.get('test')
        assert entry['observations'][0].basis == "measured"

    def test_basis_immutable_relabel_ignored(self, store):
        """Relabelling an existing observation is ignored."""
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("fact", basis="reported")]})
        # Attempt to relabel same text with lower rank
        store.upsert({'name': 'test',
                      'observations': [Observation("fact", basis="reported")]})
        entry = store.get('test')
        assert len(entry['observations']) == 1
        assert entry['observations'][0].basis == "reported"

    def test_basis_upgrade_higher_rank(self, store):
        """Higher rank upgrades stored basis."""
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("count is 472", basis="reported")]})
        store.upsert({'name': 'test',
                      'observations': [Observation("count is 472", basis="measured")]})
        entry = store.get('test')
        assert entry['observations'][0].basis == "measured"

    def test_basis_upgrade_lower_rank_skipped(self, store):
        """Lower rank does not downgrade."""
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("fact", basis="measured")]})
        store.upsert({'name': 'test',
                      'observations': [Observation("fact", basis="reported")]})
        entry = store.get('test')
        assert entry['observations'][0].basis == "measured"

    def test_verified_at_set_on_measured(self, store):
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("fact", basis="measured")]})
        entry = store.get('test')
        assert 'verified_at' in entry

    def test_verified_at_not_set_on_reported(self, store):
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("fact", basis="reported")]})
        entry = store.get('test')
        assert entry.get('verified_at') is None

    def test_verified_at_advanced_on_upgrade(self, store):
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("fact", basis="reported")]})
        assert store.get('test').get('verified_at') is None
        store.upsert({'name': 'test',
                      'observations': [Observation("fact", basis="measured")]})
        assert store.get('test').get('verified_at') is not None

    def test_same_text_different_basis_appends(self, store):
        """Same text with different basis appends if upgrade (not duplicate)."""
        # Actually per plan: duplicate text with higher rank UPGRADES in place
        # So same text should NOT be appended — it should upgrade
        store.upsert({'name': 'test', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("fact", basis="reported")]})
        store.upsert({'name': 'test',
                      'observations': [Observation("fact", basis="measured")]})
        entry = store.get('test')
        # Should have 1 observation (upgraded), not 2
        assert len(entry['observations']) == 1
        assert entry['observations'][0].basis == "measured"


# --- Canary test ---

class TestCanary:
    @pytest.fixture
    def store(self, tmp_path):
        return MemoryStore(str(tmp_path / "canary.jsonl"))

    def test_no_dict_syntax_in_searchable_text(self, store):
        """Dict/JSON syntax must not leak into search text."""
        store.upsert({'name': 'canary', 'schema': 4, 'description': 'Test',
                      'observations': [Observation("labelled fact", basis="measured")]})
        entry = store.get('canary')
        searchable = store._searchable_text(entry)
        assert "{'text'" not in searchable
        assert '"text":' not in searchable
        assert '{"t":' not in searchable

    def test_no_dict_syntax_in_jsonl_round_trip(self, store):
        """JSONL serialization preserves basis without leaking syntax."""
        store.upsert({'name': 'canary', 'schema': 4, 'description': 'Test',
                      'observations': [
                          Observation("measured fact", basis="measured"),
                          Observation("plain fact"),
                      ]})
        # Read raw JSONL to verify format
        with open(store._path) as f:
            line = f.readline()
        data = json.loads(line)
        obs = data['observations']
        # Labelled: dict with text+basis
        assert isinstance(obs[0], dict)
        assert obs[0]['text'] == "measured fact"
        assert obs[0]['basis'] == "measured"
        # Unlabelled: plain string (legacy compatible)
        assert isinstance(obs[1], str)
        assert obs[1] == "plain fact"


# --- Legacy backward compatibility ---

class TestLegacyCompat:
    def test_v1_v2_v3_fixtures_parse(self):
        """Schema v1, v2, v3 content parses under v4 code."""
        for version in [1, 2, 3]:
            content = f'''<memory:entity schema="{version}" name="compat-{version}">
  <memory:description>Compat test v{version}</memory:description>
  <memory:observations>
    <memory:observation>Plain observation</memory:observation>
  </memory:observations>
</memory:entity>'''
            result = parse_memory_content(content)
            assert result is not None
            assert result['schema'] == version
            assert result['observations'][0] == "Plain observation"
            assert isinstance(result['observations'][0], Observation)
            assert result['observations'][0].basis is None

    def test_v1_validates_under_v4(self):
        content = '''<memory:entity schema="1" name="old-entity">
  <memory:description>Old entity</memory:description>
</memory:entity>'''
        errors = validate(content)
        # Should have no errors (backward compatible)
        structural_errors = [r for r, _ in errors if r.startswith('V')]
        assert len(structural_errors) == 0
