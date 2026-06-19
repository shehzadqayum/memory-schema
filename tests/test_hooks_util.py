"""Tests for shared hook management utilities (_hooks_util.py)."""

import json

import pytest

from memoryschema.cli._hooks_util import (
    HOOK_MATCHER,
    LEGACY_MATCHERS,
    hook_already_registered,
    read_settings,
    register_hooks,
    unregister_hooks,
    write_settings,
)


# ---------------------------------------------------------------------------
# hook_already_registered
# ---------------------------------------------------------------------------

class TestHookAlreadyRegistered:
    def test_empty_settings(self):
        assert hook_already_registered({}) == (False, None)

    def test_no_hooks_key(self):
        assert hook_already_registered({"other": 1}) == (False, None)

    def test_write_matcher_with_memoryschema(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /path/memoryschema/hook.sh"}
            ]}
        ]}}
        found, cmd = hook_already_registered(settings)
        assert found is True
        assert "memoryschema" in cmd

    def test_write_edit_matcher_with_memoryschema(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hooks/hook-post-write.sh"}
            ]}
        ]}}
        found, cmd = hook_already_registered(settings)
        assert found is True
        assert "memoryschema" in cmd

    def test_unrelated_hooks_only(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /other/tool/hook.sh"}
            ]}
        ]}}
        assert hook_already_registered(settings) == (False, None)

    def test_different_matcher_ignored(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [
                {"type": "command", "command": "bash /path/memoryschema/hook.sh"}
            ]}
        ]}}
        assert hook_already_registered(settings) == (False, None)

    def test_custom_fragment(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /path/my-custom-hook.sh"}
            ]}
        ]}}
        found, cmd = hook_already_registered(settings, "my-custom")
        assert found is True


# ---------------------------------------------------------------------------
# register_hooks
# ---------------------------------------------------------------------------

class TestRegisterHooks:
    def test_empty_settings(self):
        settings = {}
        result = register_hooks(settings, "bash /hook.sh")
        assert len(result["hooks"]["PostToolUse"]) == 1
        assert result["hooks"]["PostToolUse"][0]["matcher"] == HOOK_MATCHER
        assert result["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == "bash /hook.sh"

    def test_with_stop_hook(self):
        settings = {}
        result = register_hooks(settings, "bash /hook.sh", "bash /stop.sh")
        assert "Stop" in result["hooks"]
        assert len(result["hooks"]["Stop"]) == 1
        assert result["hooks"]["Stop"][0]["hooks"][0]["command"] == "bash /stop.sh"
        assert result["hooks"]["Stop"][0]["hooks"][0]["timeout"] == 5

    def test_without_stop_hook(self):
        settings = {}
        result = register_hooks(settings, "bash /hook.sh")
        assert "Stop" not in result["hooks"]

    def test_preserves_existing_hooks(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [{"command": "other"}]}
        ]}}
        result = register_hooks(settings, "bash /hook.sh")
        assert len(result["hooks"]["PostToolUse"]) == 2

    def test_post_tool_use_timeout(self):
        result = register_hooks({}, "bash /hook.sh")
        assert result["hooks"]["PostToolUse"][0]["hooks"][0]["timeout"] == 10


# ---------------------------------------------------------------------------
# unregister_hooks
# ---------------------------------------------------------------------------

class TestUnregisterHooks:
    def test_removes_memoryschema_post_tool_use(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        result, removed = unregister_hooks(settings)
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
        result, removed = unregister_hooks(settings)
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
        result, removed = unregister_hooks(settings)
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
        result, removed = unregister_hooks(settings)
        assert len(removed) == 2
        assert len(result["hooks"]["PostToolUse"]) == 2
        assert len(result["hooks"]["Stop"]) == 1

    def test_no_matching_hooks(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [{"command": "node /aurora/hook.js"}]}
        ]}}
        result, removed = unregister_hooks(settings)
        assert len(removed) == 0
        assert len(result["hooks"]["PostToolUse"]) == 1

    def test_empty_settings(self):
        result, removed = unregister_hooks({})
        assert len(removed) == 0


# ---------------------------------------------------------------------------
# read_settings / write_settings
# ---------------------------------------------------------------------------

class TestReadWriteSettings:
    def test_read_missing_file(self, tmp_path):
        assert read_settings(tmp_path / "nonexistent.json") == {}

    def test_read_valid_json(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text('{"hooks": {}}')
        assert read_settings(settings_file) == {"hooks": {}}

    def test_write_creates_backup(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text('{"old": true}')
        write_settings(settings_file, {"new": True}, backup=True)
        backup = tmp_path / "settings.json.memory-schema-backup"
        assert backup.exists()
        assert json.loads(backup.read_text()) == {"old": True}

    def test_write_no_backup_if_missing(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        write_settings(settings_file, {"new": True}, backup=True)
        assert settings_file.exists()
        assert not (tmp_path / "settings.json.memory-schema-backup").exists()

    def test_write_valid_json_with_newline(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        write_settings(settings_file, {"key": "value"})
        content = settings_file.read_text()
        assert content.endswith("\n")
        assert json.loads(content) == {"key": "value"}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_hook_matcher_value(self):
        assert HOOK_MATCHER == "Write|Edit"

    def test_legacy_matchers_includes_both(self):
        assert "Write" in LEGACY_MATCHERS
        assert "Write|Edit" in LEGACY_MATCHERS
