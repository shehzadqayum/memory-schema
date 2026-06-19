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
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=tmp_path / "nonexistent.json"):
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
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/path/hook-post-write.sh"):
                result = runner.invoke(cli, ["hook", "status"])
        assert result.exit_code == 0
        assert "registered" in result.output.lower() or "yes" in result.output.lower()


    def test_status_detects_legacy_write_matcher(self, runner, tmp_path):
        """Backward compat: status finds hooks with old 'Write' matcher."""
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /path/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/path/hook-post-write.sh"):
                result = runner.invoke(cli, ["hook", "status"])
        assert result.exit_code == 0
        assert "registered" in result.output.lower() or "yes" in result.output.lower()

    def test_status_shows_stop_hook(self, runner, tmp_path):
        """Status reports Stop hook registration state."""
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {
                "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                    {"type": "command", "command": "bash /path/hook-post-write.sh", "timeout": 10}
                ]}],
                "Stop": [{"hooks": [
                    {"type": "command", "command": "bash /path/hook-stop.sh", "timeout": 5}
                ]}]
            }
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/path/hook-post-write.sh"):
                with patch("memoryschema.cli.hook_cmd.find_stop_hook_script_path", return_value="/path/hook-stop.sh"):
                    result = runner.invoke(cli, ["hook", "status"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "posttooluse:" in output and "yes" in output
        assert "stop:" in output and "yes" in output

    def test_status_with_new_matcher(self, runner, tmp_path):
        """Status finds hooks with new 'Write|Edit' matcher."""
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /path/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/path/hook-post-write.sh"):
                result = runner.invoke(cli, ["hook", "status"])
        assert result.exit_code == 0
        assert "registered" in result.output.lower() or "yes" in result.output.lower()


class TestHookInstall:
    def test_install_creates_entry(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text("{}")
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/pkg/memoryschema/hook-post-write.sh"):
                with patch("memoryschema.cli.hook_cmd.find_stop_hook_script_path", return_value="/pkg/hook-stop.sh"):
                    with patch("os.path.exists", return_value=True):
                        result = runner.invoke(cli, ["hook", "install"])
        assert result.exit_code == 0
        assert "Registered" in result.output
        data = json.loads(settings.read_text())
        assert len(data["hooks"]["PostToolUse"]) == 1
        assert data["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit"

    def test_install_creates_stop_entry(self, runner, tmp_path):
        """Install creates both PostToolUse and Stop hook entries."""
        settings = tmp_path / "settings.json"
        settings.write_text("{}")
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/pkg/memoryschema/hook-post-write.sh"):
                with patch("memoryschema.cli.hook_cmd.find_stop_hook_script_path", return_value="/pkg/hook-stop.sh"):
                    with patch("os.path.exists", return_value=True):
                        result = runner.invoke(cli, ["hook", "install"])
        assert result.exit_code == 0
        data = json.loads(settings.read_text())
        assert "Stop" in data["hooks"]
        assert len(data["hooks"]["Stop"]) == 1
        assert "hook-stop.sh" in data["hooks"]["Stop"][0]["hooks"][0]["command"]

    def test_install_idempotent(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/pkg/memoryschema/hook-post-write.sh"):
                with patch("os.path.exists", return_value=True):
                    result = runner.invoke(cli, ["hook", "install"])
        assert "already registered" in result.output.lower()


class TestHookUninstall:
    def test_uninstall(self, runner, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/pkg/memoryschema/hook-post-write.sh"):
                result = runner.invoke(cli, ["hook", "uninstall"])
        assert result.exit_code == 0
        assert "unregistered" in result.output.lower()


    def test_uninstall_removes_stop_entry(self, runner, tmp_path):
        """Uninstall removes both PostToolUse and Stop hook entries."""
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {
                "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                    {"type": "command", "command": "bash /pkg/memoryschema/hook-post-write.sh", "timeout": 10}
                ]}],
                "Stop": [{"hooks": [
                    {"type": "command", "command": "bash /pkg/hook-stop.sh", "timeout": 5}
                ]}]
            }
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/pkg/memoryschema/hook-post-write.sh"):
                with patch("memoryschema.cli.hook_cmd.find_stop_hook_script_path", return_value="/pkg/hook-stop.sh"):
                    result = runner.invoke(cli, ["hook", "uninstall"])
        assert result.exit_code == 0
        assert "posttooluse" in result.output.lower() or "unregistered" in result.output.lower()
        assert "stop" in result.output.lower()
        data = json.loads(settings.read_text())
        assert len(data["hooks"]["PostToolUse"]) == 0
        assert len(data["hooks"]["Stop"]) == 0

    def test_uninstall_legacy_write_matcher(self, runner, tmp_path):
        """Backward compat: uninstall removes hooks with old 'Write' matcher."""
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook-post-write.sh", "timeout": 10}
            ]}]}
        }))
        with patch("memoryschema.cli.hook_cmd.get_settings_path", return_value=settings):
            with patch("memoryschema.cli.hook_cmd.find_hook_script_path", return_value="/pkg/memoryschema/hook-post-write.sh"):
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


class TestEmbedWithConfig:
    """Verify embed_text works with config (not just env var)."""

    def test_embed_text_accepts_config(self):
        """embed_text(text, config=config) uses config.voyage_api_key."""
        from memoryschema.config import MemoryConfig
        from unittest.mock import MagicMock
        import memoryschema.embeddings as emb_mod

        config = MemoryConfig(voyage_api_key='test-key-123')

        mock_client = MagicMock()
        mock_client.embed.return_value = MagicMock(embeddings=[[0.1] * 1024])

        # Clear cached client so config is used
        old_cache = emb_mod._cached_client
        emb_mod._cached_client = None
        try:
            with patch.object(emb_mod.voyageai, 'Client', return_value=mock_client) as mock_cls:
                result = emb_mod.embed_text('test text', config=config)
            assert len(result) == 1024
            mock_cls.assert_called_once_with(api_key='test-key-123')
        finally:
            emb_mod._cached_client = old_cache


class TestHookHelp:
    def test_group_help(self, runner):
        result = runner.invoke(cli, ["hook", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output
        assert "status" in result.output
        assert "test" in result.output
