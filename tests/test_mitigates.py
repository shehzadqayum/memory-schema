"""Tests for MITIGATES relation, criterion capture, typed force records (Phase 3)."""

import json

import pytest

from memoryschema.store import MemoryStore
from memoryschema.tags import Observation
from memoryschema.audit import log_force, VALID_FORCE_TYPES, VALID_FORCE_LEVELS


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "test.jsonl"))


# --- MITIGATES relation ---

class TestMitigates:
    def test_mitigates_accepted(self, store):
        """MITIGATES is a valid relation type."""
        store.upsert({'name': 'problem', 'schema': 4, 'description': 'A problem'})
        store.upsert({'name': 'fix', 'schema': 4, 'description': 'Partial fix',
                      'relations': [{'target': 'problem', 'type': 'MITIGATES'}]})
        entry = store.get('fix')
        assert any(r['type'] == 'MITIGATES' for r in entry['relations'])

    def test_mitigates_target_stays_active(self, store):
        """MITIGATES does not change target status — target remains active."""
        store.upsert({'name': 'issue', 'schema': 4, 'description': 'An issue'})
        store.upsert({'name': 'workaround', 'schema': 4, 'description': 'Workaround',
                      'relations': [{'target': 'issue', 'type': 'MITIGATES'}]})
        target = store.get('issue')
        assert target.get('status', 'active') == 'active'

    def test_mitigates_dampening(self, store):
        """Entries with inbound MITIGATES score slightly lower."""
        store.upsert({'name': 'mitigated', 'schema': 4, 'description': 'Mitigated entry',
                      'importance': 5})
        store.upsert({'name': 'plain', 'schema': 4, 'description': 'Plain entry',
                      'importance': 5})
        store.upsert({'name': 'mitigator', 'schema': 4, 'description': 'Mitigator',
                      'relations': [{'target': 'mitigated', 'type': 'MITIGATES'}]})
        store.compute_backlinks()
        s_mitigated = store._score_entry(store.get('mitigated'))
        s_plain = store._score_entry(store.get('plain'))
        assert s_plain > s_mitigated


# --- Criterion capture on SUPERSEDES ---

class TestCriterionCapture:
    def test_supersede_audit_has_criterion(self, store):
        """SUPERSEDES audit record includes target's description as criterion."""
        store.upsert({'name': 'old', 'schema': 4,
                      'description': 'The original problem statement'})
        store.upsert({'name': 'new', 'schema': 4, 'description': 'Fix',
                      'relations': [{'target': 'old', 'type': 'SUPERSEDES'}]})
        # Read audit
        with open(store._audit_path) as f:
            records = [json.loads(line) for line in f]
        supersede_records = [r for r in records if r.get('operation') == 'supersede']
        assert len(supersede_records) >= 1
        assert supersede_records[0]['changes']['criterion'] == 'The original problem statement'
        assert supersede_records[0]['changes']['superseded_by'] == 'new'


# --- Typed force records ---

class TestForceRecords:
    def test_supersedes_emits_force(self, store):
        """SUPERSEDES relation emits a supersession force record."""
        store.upsert({'name': 'target', 'schema': 4, 'description': 'T'})
        store.upsert({'name': 'source', 'schema': 4, 'description': 'S',
                      'relations': [{'target': 'target', 'type': 'SUPERSEDES'}]})
        with open(store._audit_path) as f:
            records = [json.loads(line) for line in f]
        force_records = [r for r in records if r.get('operation') == 'force']
        assert any(r['force_type'] == 'supersession' and r['target'] == 'target'
                   for r in force_records)

    def test_contradicts_emits_force(self, store):
        """CONTRADICTS relation emits a contradiction force record."""
        store.upsert({'name': 'a', 'schema': 4, 'description': 'A'})
        store.upsert({'name': 'b', 'schema': 4, 'description': 'B',
                      'relations': [{'target': 'a', 'type': 'CONTRADICTS'}]})
        with open(store._audit_path) as f:
            records = [json.loads(line) for line in f]
        force_records = [r for r in records if r.get('operation') == 'force']
        assert any(r['force_type'] == 'contradiction' and r['target'] == 'a'
                   for r in force_records)

    def test_log_force_world_change(self, tmp_path):
        """log_force writes a well-formed world-change record."""
        audit_path = str(tmp_path / 'audit.jsonl')
        log_force(audit_path, 'world-change', 'my-entity', level='entry')
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['operation'] == 'force'
        assert record['force_type'] == 'world-change'
        assert record['target'] == 'my-entity'
        assert record['level'] == 'entry'

    def test_log_force_invalid_type(self):
        """Invalid force_type is rejected."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            with pytest.raises(ValueError, match='force_type'):
                log_force(f.name, 'invalid', 'target')

    def test_log_force_invalid_level(self):
        """Invalid level is rejected."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            with pytest.raises(ValueError, match='level'):
                log_force(f.name, 'world-change', 'target', level='invalid')
