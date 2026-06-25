"""Tests for salience instrumentation — decline logging (Phase 6)."""

import json

import pytest

from memoryschema.audit import log_decline


class TestLogDecline:
    def test_basic_decline(self, tmp_path):
        """log_decline writes a write_decline record."""
        audit_path = str(tmp_path / 'audit.jsonl')
        log_decline(audit_path, reason='mechanical test output')
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['operation'] == 'write_decline'
        assert record['reason'] == 'mechanical test output'
        assert 'timestamp' in record

    def test_with_name_hint(self, tmp_path):
        """name_hint included when provided."""
        audit_path = str(tmp_path / 'audit.jsonl')
        log_decline(audit_path, name_hint='session-state', reason='duplicate')
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['name_hint'] == 'session-state'

    def test_with_context_hash(self, tmp_path):
        """context_hash included when provided."""
        audit_path = str(tmp_path / 'audit.jsonl')
        log_decline(audit_path, reason='not novel', context_hash='abc123')
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert record['context_hash'] == 'abc123'

    def test_no_name_hint(self, tmp_path):
        """name_hint omitted when None."""
        audit_path = str(tmp_path / 'audit.jsonl')
        log_decline(audit_path, reason='test')
        with open(audit_path) as f:
            record = json.loads(f.readline())
        assert 'name_hint' not in record

    def test_append_only(self, tmp_path):
        """Multiple declines append, don't overwrite."""
        audit_path = str(tmp_path / 'audit.jsonl')
        log_decline(audit_path, reason='first')
        log_decline(audit_path, reason='second')
        with open(audit_path) as f:
            lines = f.readlines()
        assert len(lines) == 2


class TestDeclineCLI:
    def test_decline_command(self):
        """CLI decline command writes audit record."""
        from click.testing import CliRunner
        from memoryschema.cli.main import cli
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp:
            memory_dir = os.path.join(tmp, 'memory')
            os.makedirs(memory_dir)
            result = CliRunner().invoke(cli, [
                '--root', tmp, 'decline',
                '--reason', 'test decline reason'
            ])
            assert result.exit_code == 0
            assert 'Decline recorded' in result.output

            audit_path = os.path.join(memory_dir, 'audit.jsonl')
            assert os.path.exists(audit_path)
            with open(audit_path) as f:
                record = json.loads(f.readline())
            assert record['operation'] == 'write_decline'
            assert record['reason'] == 'test decline reason'
