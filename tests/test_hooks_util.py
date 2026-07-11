"""Tests for shared hook management utilities (_hooks_util.py)."""

import json

import pytest

from unittest.mock import patch

from memoryschema.cli._hooks_util import (
    HOOK_MATCHER,
    HOOK_VERSION,
    LEGACY_MATCHERS,
    detect_hook_version,
    find_project_settings,
    get_hook_registration_detail,
    hook_already_registered,
    read_settings,
    register_hooks,
    unregister_hooks,
    upgrade_hooks,
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
                    {"command": "node /example/hook.js"}
                ]}
            ],
            "Stop": [
                {"hooks": [{"command": "node /example/stop.js"}]},
                {"hooks": [{"command": "bash /path/hook-stop.sh"}]}
            ]
        }}
        result, removed = unregister_hooks(settings)
        assert len(removed) == 2
        assert len(result["hooks"]["PostToolUse"]) == 2
        assert len(result["hooks"]["Stop"]) == 1

    def test_no_matching_hooks(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "*", "hooks": [{"command": "node /example/hook.js"}]}
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

    def test_hook_version(self):
        assert HOOK_VERSION == "2"


# ---------------------------------------------------------------------------
# get_hook_registration_detail
# ---------------------------------------------------------------------------

class TestGetHookRegistrationDetail:
    def test_not_installed(self):
        detail = get_hook_registration_detail({})
        assert detail["post_tool_use_registered"] is False
        assert detail["stop_registered"] is False
        assert detail["needs_upgrade"] is False

    def test_stale_write_matcher(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook.sh", "timeout": 10}
            ]}
        ]}}
        detail = get_hook_registration_detail(settings)
        assert detail["post_tool_use_registered"] is True
        assert detail["post_tool_use_stale"] is True
        assert detail["post_tool_use_matcher"] == "Write"
        assert detail["needs_upgrade"] is True
        assert any("Write" in r for r in detail["upgrade_reasons"])

    def test_missing_stop_hook(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh", "timeout": 10}
            ]}
        ]}}
        detail = get_hook_registration_detail(settings)
        assert detail["post_tool_use_registered"] is True
        assert detail["post_tool_use_stale"] is False
        assert detail["stop_registered"] is False
        assert detail["needs_upgrade"] is True
        assert any("Stop" in r for r in detail["upgrade_reasons"])

    def test_all_current_v2(self):
        settings = {"hooks": {
            "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh", "timeout": 10}
            ]}],
            "Stop": [{"hooks": [
                {"command": "bash /pkg/hook-stop.sh", "timeout": 5}
            ]}]
        }}
        detail = get_hook_registration_detail(settings)
        assert detail["post_tool_use_registered"] is True
        assert detail["post_tool_use_stale"] is False
        assert detail["stop_registered"] is True
        assert detail["needs_upgrade"] is False
        assert detail["upgrade_reasons"] == []

    def test_script_existence_check(self, tmp_path):
        script_dir = tmp_path / "memoryschema" / "hooks"
        script_dir.mkdir(parents=True)
        script = script_dir / "hook-post-write.sh"
        script.write_text("#!/bin/bash\nexit 0\n")
        script.chmod(0o755)
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"command": f"bash {script}", "timeout": 10}
            ]}
        ]}}
        detail = get_hook_registration_detail(settings)
        assert detail["post_tool_use_script_exists"] is True
        assert detail["post_tool_use_script_executable"] is True


# ---------------------------------------------------------------------------
# detect_hook_version
# ---------------------------------------------------------------------------

class TestDetectHookVersion:
    def test_v0_not_installed(self):
        detail = get_hook_registration_detail({})
        assert detect_hook_version(detail) == "0"

    def test_v1_stale_matcher(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        detail = get_hook_registration_detail(settings)
        assert detect_hook_version(detail) == "1"

    def test_v1_missing_stop(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        detail = get_hook_registration_detail(settings)
        assert detect_hook_version(detail) == "1"

    def test_v2_current(self):
        settings = {"hooks": {
            "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}],
            "Stop": [{"hooks": [
                {"command": "bash /pkg/hook-stop.sh"}
            ]}]
        }}
        detail = get_hook_registration_detail(settings)
        assert detect_hook_version(detail) == "2"


# ---------------------------------------------------------------------------
# upgrade_hooks
# ---------------------------------------------------------------------------

class TestUpgradeHooks:
    def test_upgrade_write_to_write_edit(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh", "timeout": 10}
            ]}
        ]}}
        changes = upgrade_hooks(settings, "/pkg/hook.sh", "/pkg/stop.sh")
        assert len(changes) >= 1
        assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit"
        assert any("Write|Edit" in c for c in changes)

    def test_upgrade_adds_stop_hook(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        changes = upgrade_hooks(settings, "/pkg/hook.sh", "/pkg/stop.sh")
        assert len(changes) >= 1
        assert "Stop" in settings["hooks"]
        assert any("Stop" in c for c in changes)

    def test_upgrade_both(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        changes = upgrade_hooks(settings, "/pkg/hook.sh", "/pkg/stop.sh")
        assert len(changes) == 2
        assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit"
        assert "Stop" in settings["hooks"]

    def test_already_current_no_changes(self):
        settings = {"hooks": {
            "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}],
            "Stop": [{"hooks": [
                {"command": "bash /pkg/hook-stop.sh"}
            ]}]
        }}
        changes = upgrade_hooks(settings, "/pkg/hook.sh", "/pkg/stop.sh")
        assert changes == []

    def test_no_stop_path_skips_stop_add(self):
        settings = {"hooks": {"PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"command": "bash /pkg/memoryschema/hook.sh"}
            ]}
        ]}}
        changes = upgrade_hooks(settings, "/pkg/hook.sh", None)
        assert changes == []


# ---------------------------------------------------------------------------
# find_project_settings
# ---------------------------------------------------------------------------

class TestFindProjectSettings:
    def test_finds_global(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{}")
        with patch("memoryschema.cli._hooks_util.get_settings_path",
                   return_value=claude_dir / "settings.json"):
            results = find_project_settings(scan_dirs=[])
        assert len(results) >= 1
        assert results[0]["scope"] == "global"

    def test_finds_project_settings(self, tmp_path):
        # Create a project with .claude/settings.json
        project = tmp_path / "my-project"
        project.mkdir()
        (project / ".claude").mkdir()
        (project / ".claude" / "settings.json").write_text("{}")
        # Mock global as non-existent
        with patch("memoryschema.cli._hooks_util.get_settings_path",
                   return_value=tmp_path / "nonexistent" / "settings.json"):
            results = find_project_settings(scan_dirs=[tmp_path])
        project_results = [r for r in results if r["scope"] == "project"]
        assert len(project_results) >= 1
        assert project_results[0]["project_name"] == "my-project"

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".hidden-project"
        hidden.mkdir()
        (hidden / ".claude").mkdir()
        (hidden / ".claude" / "settings.json").write_text("{}")
        with patch("memoryschema.cli._hooks_util.get_settings_path",
                   return_value=tmp_path / "nonexistent" / "settings.json"):
            results = find_project_settings(scan_dirs=[tmp_path])
        project_names = [r["project_name"] for r in results]
        assert ".hidden-project" not in project_names

    def test_skips_missing_scan_dirs(self, tmp_path):
        with patch("memoryschema.cli._hooks_util.get_settings_path",
                   return_value=tmp_path / "nonexistent" / "settings.json"):
            results = find_project_settings(scan_dirs=[tmp_path / "does-not-exist"])
        # Should not crash, just return empty or global-only
        assert isinstance(results, list)
