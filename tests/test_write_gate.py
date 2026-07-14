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

    def test_warning_missing_description(self):
        memory = {'name': 'no-desc'}
        result = gate_pipeline(memory)
        assert result.verdict == GateVerdict.ACCEPT
        assert any('description' in w.lower() for w in result.warnings)

    def test_accept_upsert(self, store):
        store.upsert({'name': 'existing', 'schema': 3, 'description': 'First'})
        memory = {'name': 'existing', 'description': 'Updated'}
        result = gate_pipeline(memory, store=store)
        assert result.verdict == GateVerdict.ACCEPT


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
                          ['passed all checks'])
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['operation'] == 'gate_decision'
        assert record['name'] == 'test-entry'
        assert record['verdict'] == 'accept'

    def test_log_gate_decision_reject(self, tmp_path):
        from memoryschema.audit import log_gate_decision
        audit_path = str(tmp_path / 'audit.jsonl')
        log_gate_decision(audit_path, 'bad-entry', 'reject',
                          ['Missing name attribute'])
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['verdict'] == 'reject'
        assert 'Missing name' in record['reasons'][0]


class TestGateStrictConfig:
    """gate.strict (config) enables stage 2 without the caller passing strict=True (A2)."""
    def _dup(self, store):
        # an existing entry + a differently-described near-duplicate embedding (cosine 1.0)
        store.upsert({'name': 'orig', 'schema': 5, 'description': 'alpha topic',
                      'embedding': [1.0, 0.0, 0.0, 0.0]})
        return {'name': 'dup', 'description': 'totally different words here',
                'embedding': [1.0, 0.0, 0.0, 0.0]}

    def test_dormant_by_default(self, store):
        r = gate_pipeline(self._dup(store), store=store)          # no config, strict defaults False
        assert r.verdict == GateVerdict.ACCEPT                     # stage 2 dormant

    def test_config_gate_strict_enables_stage2(self, store):
        from memoryschema.config import MemoryConfig
        cfg = MemoryConfig(project_root='.', gate_strict=True)
        r = gate_pipeline(self._dup(store), store=store, config=cfg)
        assert r.verdict == GateVerdict.QUARANTINE                 # config flipped stage 2 on


class TestForwardReferenceWarning:
    """v0.1.2 (defect 3): a relation target absent from the store warns — never blocks."""

    def test_missing_target_warns_existing_does_not(self, store):
        store.upsert({'name': 'known', 'schema': 5, 'description': 'K'})
        memory = {'name': 'n', 'description': 'd',
                  'relations': [{'type': 'USES', 'target': 'ghost'},
                                {'type': 'USES', 'target': 'known'}]}
        result = gate_pipeline(memory, store=store)
        assert result.verdict == GateVerdict.ACCEPT                # advisory only
        joined = ' | '.join(result.warnings)
        assert "'ghost'" in joined and 'forward reference' in joined
        assert "'known'" not in joined

    def test_no_store_no_probe(self):
        memory = {'name': 'n', 'description': 'd',
                  'relations': [{'type': 'USES', 'target': 'ghost'}]}
        result = gate_pipeline(memory)                             # store=None -> probe skipped
        assert result.verdict == GateVerdict.ACCEPT
        assert not any('forward reference' in w for w in result.warnings)
