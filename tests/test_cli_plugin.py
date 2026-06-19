"""Tests for CLI plugin management commands (deploy, uninstall, status)."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from memoryschema.cli.plugin_cmd import (
    _add_hook,
    _hook_already_registered,
    _remove_hook,
)


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# 1.1 _hook_already_registered
# ---------------------------------------------------------------------------

class TestHookAlreadyRegistered:
    def test_empty_settings(self):
        assert _hook_already_registered({}) == (False, None)

    def test_no_hooks_key(self):
        assert _hook_already_registered({"other": 1}) == (False, None)

    def test_write_matcher_with_memoryschema(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /path/memoryschema/hook.sh"}
            ]}
        ]}}
        found, cmd = _hook_already_registered(settings)
        assert found is True
        assert "memoryschema" in cmd

    def test_write_edit_matcher_with_memoryschema(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hooks/hook-post-write.sh"}
            ]}
        ]}}
        found, cmd = _hook_already_registered(settings)
        assert found is True
        assert "memoryschema" in cmd

    def test_unrelated_hooks_only(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /other/tool/hook.sh"}
            ]}
        ]}}
        assert _hook_already_registered(settings) == (False, None)

    def test_different_matcher_ignored(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [
                {"type": "command", "command": "bash /path/memoryschema/hook.sh"}
            ]}
        ]}}
        assert _hook_already_registered(settings) == (False, None)

    def test_custom_fragment(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /path/my-custom-hook.sh"}
            ]}
        ]}}
        found, cmd = _hook_already_registered(settings, "my-custom")
        assert found is True


# ---------------------------------------------------------------------------
# 1.2 _add_hook
# ---------------------------------------------------------------------------

class TestAddHook:
    def test_empty_settings(self):
        settings = {}
        result = _add_hook(settings, "bash /hook.sh")
        assert len(result["hooks"]["PostToolUse"]) == 1
        assert result["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit"
        assert result["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == "bash /hook.sh"

    def test_with_stop_hook(self):
        settings = {}
        result = _add_hook(settings, "bash /hook.sh", "bash /stop.sh")
        assert "Stop" in result["hooks"]
        assert len(result["hooks"]["Stop"]) == 1
        assert result["hooks"]["Stop"][0]["hooks"][0]["command"] == "bash /stop.sh"
        assert result["hooks"]["Stop"][0]["hooks"][0]["timeout"] == 5

    def test_without_stop_hook(self):
        settings = {}
        result = _add_hook(settings, "bash /hook.sh")
        assert "Stop" not in result["hooks"]

    def test_preserves_existing_hooks(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [{"command": "other"}]}
        ]}}
        result = _add_hook(settings, "bash /hook.sh")
        assert len(result["hooks"]["PostToolUse"]) == 2

    def test_post_tool_use_timeout(self):
        result = _add_hook({}, "bash /hook.sh")
        assert result["hooks"]["PostToolUse"][0]["hooks"][0]["timeout"] == 10


# ---------------------------------------------------------------------------
# 1.3 _remove_hook
# ---------------------------------------------------------------------------

class TestRemoveHook:
    def test_removes_memoryschema_post_tool_use(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        result, removed = _remove_hook(settings)
        assert len(removed) == 1
        assert "memoryschema" in removed[0]
        assert len(result["hooks"]["PostToolUse"]) == 0

    def test_removes_stop_hook(self):
        settings = {"hooks": {
            "PostToolUse": [],
            "Stop": [{"hooks": [
                {"type": "command", "command": "bash /pkg/hook-stop.sh"}
            ]}]
        }}
        result, removed = _remove_hook(settings)
        assert len(removed) == 1
        assert "hook-stop.sh" in removed[0]
        assert len(result["hooks"]["Stop"]) == 0

    def test_removes_both_hooks(self):
        settings = {"hooks": {
            "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                {"command": "bash /memoryschema/hook.sh"}
            ]}],
            "Stop": [{"hooks": [
                {"command": "bash /path/hook-stop.sh"}
            ]}]
        }}
        result, removed = _remove_hook(settings)
        assert len(removed) == 2

    def test_preserves_unrelated_hooks(self):
        settings = {"hooks": {
            "PostToolUse": [
                {"matcher": "Write|Edit", "hooks": [
                    {"command": "bash /memoryschema/hook.sh"},
                    {"command": "bash /other/hook.sh"},
                ]},
                {"matcher": "*", "hooks": [
                    {"command": "node /aurora/hook.js"}
                ]}
            ],
            "Stop": [
                {"hooks": [{"command": "node /aurora/stop.js"}]},
                {"hooks": [{"command": "bash /path/hook-stop.sh"}]}
            ]
        }}
        result, removed = _remove_hook(settings)
        assert len(removed) == 2  # memoryschema + hook-stop.sh
        # Aurora hooks preserved
        assert len(result["hooks"]["PostToolUse"]) == 2  # Write|Edit entry (with other) + * entry
        assert len(result["hooks"]["Stop"]) == 1  # aurora stop

    def test_no_matching_hooks(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [{"command": "node /aurora/hook.js"}]}
        ]}}
        result, removed = _remove_hook(settings)
        assert len(removed) == 0
        assert len(result["hooks"]["PostToolUse"]) == 1

    def test_empty_settings(self):
        result, removed = _remove_hook({})
        assert len(removed) == 0


# ---------------------------------------------------------------------------
# 1.4 _read_settings / _write_settings
# ---------------------------------------------------------------------------

class TestReadWriteSettings:
    def test_read_missing_file(self, tmp_path):
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", tmp_path):
            from memoryschema.cli.plugin_cmd import _read_settings
            assert _read_settings() == {}

    def test_read_valid_json(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text('{"hooks": {}}')
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", tmp_path):
            from memoryschema.cli.plugin_cmd import _read_settings
            result = _read_settings()
            assert result == {"hooks": {}}

    def test_write_creates_backup(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text('{"old": true}')
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", tmp_path):
            from memoryschema.cli.plugin_cmd import _write_settings
            _write_settings({"new": True})
        backup = tmp_path / "settings.json.memory-schema-backup"
        assert backup.exists()
        assert json.loads(backup.read_text()) == {"old": True}

    def test_write_no_backup_if_missing(self, tmp_path):
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", tmp_path):
            from memoryschema.cli.plugin_cmd import _write_settings
            _write_settings({"new": True})
        settings_file = tmp_path / "settings.json"
        assert settings_file.exists()
        backup = tmp_path / "settings.json.memory-schema-backup"
        assert not backup.exists()

    def test_write_valid_json_with_newline(self, tmp_path):
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", tmp_path):
            from memoryschema.cli.plugin_cmd import _write_settings
            _write_settings({"key": "value"})
        content = (tmp_path / "settings.json").read_text()
        assert content.endswith("\n")
        assert json.loads(content) == {"key": "value"}


# ---------------------------------------------------------------------------
# 1.5 _read_manifest / _write_manifest
# ---------------------------------------------------------------------------

class TestReadWriteManifest:
    def test_read_missing(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        with patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            from memoryschema.cli.plugin_cmd import _read_manifest
            assert _read_manifest() is None

    def test_read_valid(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text('{"version": "1.0"}')
        with patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            from memoryschema.cli.plugin_cmd import _read_manifest
            result = _read_manifest()
            assert result == {"version": "1.0"}

    def test_write(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        with patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            from memoryschema.cli.plugin_cmd import _write_manifest
            _write_manifest({"version": "2.0", "deployed_at": "now"})
        content = manifest_path.read_text()
        assert content.endswith("\n")
        data = json.loads(content)
        assert data["version"] == "2.0"
