"""Tests for CLI doctor command."""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestDoctor:
    def test_runs(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "doctor"])
        assert result.exit_code == 0
        assert "python" in result.output
        assert "package" in result.output
        assert "Summary" in result.output

    def test_json_output(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "doctor", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "checks" in data
        assert "summary" in data
        assert data["summary"]["total"] >= 15

    def test_passes_python_and_package(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "doctor", "--json"])
        data = json.loads(result.output)
        checks = {c["name"]: c for c in data["checks"]}
        assert checks["python"]["passed"] is True
        assert checks["package"]["passed"] is True
        assert checks["config"]["passed"] is True

    def test_fails_missing_memory_dir(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "doctor", "--json"])
        data = json.loads(result.output)
        checks = {c["name"]: c for c in data["checks"]}
        assert checks["memory_dir"]["passed"] is False
        assert checks["memory_dir"]["fix"] is not None

    def test_fix_flag(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "doctor", "--fix"])
        assert result.exit_code == 0
        assert "Auto-fixing" in result.output or "Summary" in result.output

    def test_help(self, runner):
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "diagnostic" in result.output.lower()
        assert "--json" in result.output
        assert "--fix" in result.output
