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


class TestParseNonEntityFiles:
    """Verify parse_memory_file returns None for non-entity files (Phase 0)."""

    def test_yaml_frontmatter_returns_none(self, tmp_path):
        """Auto-memory YAML frontmatter files are not memory entities."""
        from memoryschema.tags import parse_memory_file
        f = tmp_path / "auto-memory.md"
        f.write_text("---\nname: test\ntype: project\n---\n\nSome content.\n")
        assert parse_memory_file(str(f)) is None

    def test_plain_markdown_returns_none(self, tmp_path):
        """Plain markdown without entity block returns None."""
        from memoryschema.tags import parse_memory_file
        f = tmp_path / "plain.md"
        f.write_text("# Title\n\nJust some markdown text.\n")
        assert parse_memory_file(str(f)) is None

    def test_valid_entity_returns_dict(self, tmp_path):
        """Verify real entity files still parse correctly."""
        from memoryschema.tags import parse_memory_file
        f = tmp_path / "valid.md"
        f.write_text(
            '<memory:entity schema="4" name="test-entity">\n'
            '  <memory:description>A test entity</memory:description>\n'
            '</memory:entity>\n'
        )
        result = parse_memory_file(str(f))
        assert result is not None
        assert result['name'] == 'test-entity'


class TestHookHelp:
    def test_group_help(self, runner):
        result = runner.invoke(cli, ["hook", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output
        assert "status" in result.output
        assert "test" in result.output
