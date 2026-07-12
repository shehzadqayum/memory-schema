"""Tests for numeric contradiction probe and L0 echo probe (Phase 4)."""

import json
import os

import pytest

from memoryschema.numeric_probe import extract_claims, compare, extract_entity_claims
from memoryschema.write_gate import gate_pipeline, GateVerdict
from memoryschema.store import MemoryStore
from memoryschema.tags import observation_text, serialize_observation, deserialize_observation


# --- extract_claims ---

class TestExtractClaims:
    def test_basic_number_unit(self):
        claims = extract_claims("472 tests passing")
        assert (472.0, 'test', 'passing') in claims

    def test_bare_number_unit(self):
        claims = extract_claims("27 files")
        assert (27.0, 'file', None) in claims

    def test_unit_colon_number(self):
        claims = extract_claims("tests: 472")
        assert (472.0, 'test', None) in claims

    def test_unit_equals_number(self):
        claims = extract_claims("checks=21")
        assert (21.0, 'check', None) in claims

    def test_qualifier_separation(self):
        """5 tests added vs 472 tests passing → different qualifiers."""
        c1 = extract_claims("5 tests added")
        c2 = extract_claims("472 tests passing")
        assert (5.0, 'test', 'added') in c1
        assert (472.0, 'test', 'passing') in c2
        # Different qualifiers → different keys

    def test_stoplist_percent(self):
        claims = extract_claims("50 percent complete")
        assert not any(u == 'percent' for _, u, _ in claims)

    def test_stoplist_version(self):
        claims = extract_claims("3 version changes")
        assert not any(u == 'version' for _, u, _ in claims)

    def test_year_excluded(self):
        claims = extract_claims("2026 sessions recorded")
        # 2026 is a year, should be excluded
        assert not any(q == 2026.0 for q, _, _ in claims)

    def test_version_token_excluded(self):
        claims = extract_claims("472 v4 entities")
        # v4 should be excluded as a version token
        assert not any(u.startswith('v') and u[1:].isdigit() for _, u, _ in claims)

    def test_comma_number(self):
        claims = extract_claims("1,234 entries stored")
        assert any(q == 1234.0 for q, _, _ in claims)

    def test_decimal_number(self):
        claims = extract_claims("0.95 threshold reached")
        assert any(q == 0.95 for q, _, _ in claims)

    def test_singularization(self):
        """'tests' → 'test', 'files' → 'file'."""
        claims = extract_claims("472 tests")
        assert any(u == 'test' for _, u, _ in claims)

    def test_empty_text(self):
        assert extract_claims("") == []
        assert extract_claims(None) == []

    def test_no_numbers(self):
        assert extract_claims("no numeric content here") == []

    def test_short_unit_excluded(self):
        """Units shorter than 3 chars excluded by regex."""
        claims = extract_claims("5 ab things")
        assert not any(u == 'ab' for _, u, _ in claims)


# --- compare ---

class TestCompare:
    def test_contradiction_detected(self):
        candidate = [(433.0, 'test', 'passing')]
        neighbours = [{'name': 'old', 'description': '472 tests passing',
                       'observations': []}]
        hits = compare(candidate, neighbours)
        assert len(hits) >= 1
        assert hits[0]['candidate_value'] == 433.0
        assert hits[0]['neighbour_value'] == 472.0

    def test_no_contradiction_different_qualifier(self):
        """Different qualifiers → no hit."""
        candidate = [(5.0, 'test', 'added')]
        neighbours = [{'name': 'old', 'description': '472 tests passing',
                       'observations': []}]
        hits = compare(candidate, neighbours)
        assert len(hits) == 0

    def test_same_value_no_hit(self):
        candidate = [(472.0, 'test', 'passing')]
        neighbours = [{'name': 'old', 'description': '472 tests passing',
                       'observations': []}]
        hits = compare(candidate, neighbours)
        assert len(hits) == 0

    def test_bare_claims_match(self):
        """Bare "433 tests" vs bare "472 tests" → hit (both qualifier=None)."""
        candidate = [(433.0, 'test', None)]
        neighbours = [{'name': 'old', 'description': '',
                       'observations': ['472 tests']}]
        hits = compare(candidate, neighbours)
        assert len(hits) >= 1


# --- Gate integration ---

class TestGateNumericProbe:
    @pytest.fixture
    def store(self, tmp_path):
        s = MemoryStore(str(tmp_path / "probe.jsonl"))
        s.upsert({'name': 'session-10-state', 'schema': 4,
                  'description': 'Session 10 final state',
                  'observations': ['472 tests passing across 27 files'],
                  'embedding': [1.0, 0.0, 0.0]})
        return s

    def test_probe_log_mode_does_not_quarantine(self, store):
        """Default log mode: hit logged as warning, not quarantine."""
        from unittest.mock import MagicMock
        config = MagicMock()
        config.numeric_probe_enabled = True
        config.numeric_probe_mode = 'log'
        config.numeric_probe_sim_threshold = 0.80
        config.l0_echo_threshold = 0.6
        config.gate_strict = False   # stage 2 dormant (MagicMock would otherwise auto-truthy this)

        memory = {'name': 'new', 'description': 'Test',
                  'observations': ['433 tests passing'],
                  'embedding': [0.99, 0.0, 0.0]}  # high sim
        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT
        assert any('numeric-probe-hit' in w for w in result.warnings)

    def test_probe_quarantine_mode(self, store):
        """Quarantine mode: hit → QUARANTINE."""
        from unittest.mock import MagicMock
        config = MagicMock()
        config.numeric_probe_enabled = True
        config.numeric_probe_mode = 'quarantine'
        config.numeric_probe_sim_threshold = 0.80
        config.l0_echo_threshold = 0.6
        config.gate_strict = False   # stage 2 dormant (MagicMock would otherwise auto-truthy this)

        memory = {'name': 'new', 'description': 'Test',
                  'observations': ['433 tests passing'],
                  'embedding': [0.99, 0.0, 0.0]}
        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.QUARANTINE
        assert any('numeric-contradiction' in r for r in result.reasons)

    def test_contradicts_bypass(self, store):
        """Declared CONTRADICTS bypasses the probe."""
        from unittest.mock import MagicMock
        config = MagicMock()
        config.numeric_probe_enabled = True
        config.numeric_probe_mode = 'quarantine'
        config.numeric_probe_sim_threshold = 0.80
        config.l0_echo_threshold = 0.6
        config.gate_strict = False   # stage 2 dormant (MagicMock would otherwise auto-truthy this)

        memory = {'name': 'new', 'description': 'Test',
                  'observations': ['433 tests passing'],
                  'embedding': [0.99, 0.0, 0.0],
                  'relations': [{'target': 'session-10-state', 'type': 'CONTRADICTS'}]}
        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT

    def test_supersedes_bypass(self, store):
        """Declared SUPERSEDES bypasses the probe."""
        from unittest.mock import MagicMock
        config = MagicMock()
        config.numeric_probe_enabled = True
        config.numeric_probe_mode = 'quarantine'
        config.numeric_probe_sim_threshold = 0.80
        config.l0_echo_threshold = 0.6
        config.gate_strict = False   # stage 2 dormant (MagicMock would otherwise auto-truthy this)

        memory = {'name': 'new', 'description': 'Test',
                  'observations': ['433 tests passing'],
                  'embedding': [0.99, 0.0, 0.0],
                  'relations': [{'target': 'session-10-state', 'type': 'SUPERSEDES'}]}
        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT

    def test_no_embedding_skips(self, store):
        """No embedding → stages 5-6 skip with warning."""
        from unittest.mock import MagicMock
        config = MagicMock()
        config.numeric_probe_enabled = True
        config.numeric_probe_mode = 'quarantine'
        config.l0_echo_threshold = 0.6
        config.gate_strict = False   # stage 2 dormant (MagicMock would otherwise auto-truthy this)

        memory = {'name': 'new', 'description': 'Test',
                  'observations': ['433 tests passing']}
        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT
        assert any('skipped' in w for w in result.warnings)


# --- L0 echo probe ---

class TestL0Echo:
    def test_echo_quarantined(self, tmp_path):
        """High overlap + no measured + no external relation → QUARANTINE."""
        # Create MEMORY.md
        memory_dir = tmp_path / 'memory'
        memory_dir.mkdir()
        (memory_dir / 'MEMORY.md').write_text(
            '- [existing-entry](existing-entry.md) -- important system architecture fact\n'
        )
        os.chdir(tmp_path)

        store = MemoryStore(str(memory_dir / 'store.jsonl'))
        memory = {'name': 'echo', 'description': 'important system architecture fact',
                  'observations': ['restated']}

        from memoryschema.write_gate import _check_l0_echo
        reasons = []
        _check_l0_echo(memory, 0.6, reasons)
        assert any('l0-echo' in r for r in reasons)

    def test_echo_with_external_relation_accepted(self, tmp_path):
        """High overlap but with external relation target → NOT echo."""
        memory_dir = tmp_path / 'memory'
        memory_dir.mkdir()
        (memory_dir / 'MEMORY.md').write_text(
            '- [existing-entry](existing-entry.md) -- important system architecture fact\n'
        )
        os.chdir(tmp_path)

        memory = {'name': 'reinforcement',
                  'description': 'important system architecture fact',
                  'observations': ['new data'],
                  'relations': [{'target': 'other-entry', 'type': 'USES'}]}

        from memoryschema.write_gate import _check_l0_echo
        reasons = []
        _check_l0_echo(memory, 0.6, reasons)
        assert len(reasons) == 0

    def test_low_overlap_accepted(self, tmp_path):
        """Low overlap → NOT echo."""
        memory_dir = tmp_path / 'memory'
        memory_dir.mkdir()
        (memory_dir / 'MEMORY.md').write_text(
            '- [existing-entry](existing-entry.md) -- completely different topic about cooking\n'
        )
        os.chdir(tmp_path)

        memory = {'name': 'new', 'description': 'system architecture and testing patterns'}

        from memoryschema.write_gate import _check_l0_echo
        reasons = []
        _check_l0_echo(memory, 0.6, reasons)
        assert len(reasons) == 0
