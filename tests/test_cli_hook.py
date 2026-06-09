"""Tests for CLI hook management commands."""

import json
import os
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestHookStatus:
    def test_status_no_settings(self, runner, tmp_path):
        with patch("memoryschema.cli.hook_cmd._settings_path", return_value=tmp_path / "nonexistent.json"):
            result = runner.invoke(cli, ["hook", "status"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "no" in result.output.lower()

    def test_status_with_hook(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /path/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd._settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd._hook_script_path", return_value="/path/hook-post-write.sh"):
                result = runner.invoke(cli, ["hook", "status"])
        assert result.exit_code == 0
        assert "registered" in result.output.lower() or "yes" in result.output.lower()


class TestHookInstall:
    def test_install_creates_entry(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text("{}")
        with patch("memoryschema.cli.hook_cmd._settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd._hook_script_path", return_value="/pkg/hook-post-write.sh"):
                with patch("os.path.exists", return_value=True):
                    result = runner.invoke(cli, ["hook", "install"])
        assert result.exit_code == 0
        assert "Registered" in result.output
        data = json.loads(settings.read_text())
        assert len(data["hooks"]["PostToolUse"]) == 1

    def test_install_idempotent(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /pkg/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd._settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd._hook_script_path", return_value="/pkg/hook-post-write.sh"):
                with patch("os.path.exists", return_value=True):
                    result = runner.invoke(cli, ["hook", "install"])
        assert "already registered" in result.output.lower()


class TestHookUninstall:
    def test_uninstall(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /pkg/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd._settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd._hook_script_path", return_value="/pkg/hook-post-write.sh"):
                result = runner.invoke(cli, ["hook", "uninstall"])
        assert result.exit_code == 0
        assert "unregistered" in result.output.lower()


class TestHookHelp:
    def test_group_help(self, runner):
        result = runner.invoke(cli, ["hook", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output
        assert "status" in result.output
        assert "test" in result.output
