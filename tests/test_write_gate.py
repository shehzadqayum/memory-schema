"""Tests for write gate pipeline."""

import json
import os

import pytest

from memoryschema.store import MemoryStore
from memoryschema.write_gate import gate_pipeline, gate_check, GateVerdict, GateResult


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "gate-test.jsonl"))


class TestGateVerdict:
    def test_accept(self):
        memory = {'name': 'test', 'description': 'Valid entry'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.ACCEPT
        assert result.ok is True

    def test_reject_missing_name(self):
        memory = {'description': 'No name'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.REJECT
        assert result.ok is False
        assert 'Missing name' in result.reasons[0]

    def test_reject_ingested_no_source(self):
        memory = {'name': 'ingested-no-src', 'description': 'Test',
                  'provenance': 'ingested'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.REJECT
        assert 'source' in result.reasons[0].lower()

    def test_accept_ingested_with_source(self):
        memory = {'name': 'ingested-ok', 'description': 'Test',
                  'provenance': 'ingested', 'source': 'http://example.com'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.ACCEPT

    def test_quarantine_provenance_mismatch(self, store):
        store.upsert({'name': 'existing', 'schema': 3, 'description': 'First',
                      'provenance': 'first-party'})
        memory = {'name': 'existing', 'description': 'Second',
                  'provenance': 'ingested', 'source': 'http://x.com'}
        result = gate_pipeline(memory, store=store)
        assert result.verdict == GateVerdict.QUARANTINE
        assert 'mismatch' in result.reasons[0].lower()

    def test_accept_same_provenance_upsert(self, store):
        store.upsert({'name': 'existing', 'schema': 3, 'description': 'First',
                      'provenance': 'first-party'})
        memory = {'name': 'existing', 'description': 'Updated'}
        result = gate_pipeline(memory, store=store)
        assert result.verdict == GateVerdict.ACCEPT

    def test_warning_no_provenance(self):
        memory = {'name': 'no-prov', 'description': 'Test'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.ACCEPT
        assert any('defaulting' in w for w in result.warnings)
        assert memory['provenance'] == 'first-party'

    def test_warning_missing_description(self):
        memory = {'name': 'no-desc'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.ACCEPT
        assert any('description' in w.lower() for w in result.warnings)


class TestGateResult:
    def test_to_dict(self):
        r = GateResult(GateVerdict.REJECT, ['bad'], ['warn'])
        d = r.to_dict()
        assert d['verdict'] == 'reject'
        assert d['reasons'] == ['bad']
        assert d['warnings'] == ['warn']


class TestBackwardCompat:
    def test_gate_check_returns_tuple(self):
        ok, warnings = gate_check({'name': 'test', 'description': 'OK'})
        assert ok is True

    def test_gate_check_reject(self):
        ok, warnings = gate_check({})
        assert ok is False
        assert len(warnings) > 0


class TestAuditLogging:
    def test_log_gate_decision(self, tmp_path):
        from memoryschema.audit import log_gate_decision
        audit_path = str(tmp_path / 'audit.jsonl')
        log_gate_decision(audit_path, 'test-entry', 'accept',
                          ['passed all checks'], provenance='first-party')
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['operation'] == 'gate_decision'
        assert record['name'] == 'test-entry'
        assert record['verdict'] == 'accept'
        assert record['provenance'] == 'first-party'

    def test_log_gate_decision_reject(self, tmp_path):
        from memoryschema.audit import log_gate_decision
        audit_path = str(tmp_path / 'audit.jsonl')
        log_gate_decision(audit_path, 'bad-entry', 'reject',
                          ['Missing name attribute'])
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['verdict'] == 'reject'
        assert 'Missing name' in record['reasons'][0]
