"""Tests for CLI plugin management commands (deploy, uninstall, status)."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli
from memoryschema.cli.plugin_cmd import (
    _add_hook,
    _hook_already_registered,
    _remove_hook,
    SKILL_FILES,
    RULE_FILES,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def plugin_dir(tmp_path):
    """Create a minimal .claude-plugin/ directory with all expected files."""
    plugin = tmp_path / ".claude-plugin"
    for src_rel, _ in SKILL_FILES:
        f = plugin / src_rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {src_rel}\n")
    for src_rel, _ in RULE_FILES:
        f = plugin / src_rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {src_rel}\n")
    return plugin


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


# ---------------------------------------------------------------------------
# 2. Deploy command tests
# ---------------------------------------------------------------------------

class TestDeploy:
    def _deploy(self, runner, tmp_path, plugin_dir, force=False, hook_path="/pkg/memoryschema/hook.sh", stop_path="/pkg/memoryschema/stop.sh"):
        """Helper to invoke deploy with all paths mocked."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        args = ["plugin", "deploy"]
        if force:
            args.append("--force")
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", claude_dir / "memory-schema-manifest.json"), \
             patch("memoryschema.cli.plugin_cmd._find_plugin_dir", return_value=plugin_dir), \
             patch("memoryschema.cli.plugin_cmd._find_hook_script", return_value=hook_path), \
             patch("memoryschema.cli.plugin_cmd._find_stop_hook_script", return_value=stop_path):
            result = runner.invoke(cli, args, catch_exceptions=False)
        return result, claude_dir

    def test_basic_deploy(self, runner, tmp_path, plugin_dir):
        result, claude_dir = self._deploy(runner, tmp_path, plugin_dir)
        assert result.exit_code == 0
        # Skills deployed
        for _, dst_rel in SKILL_FILES:
            assert (claude_dir / dst_rel).exists()
        # Rules deployed
        for _, dst_rel in RULE_FILES:
            assert (claude_dir / dst_rel).exists()
        # Memory dir created
        assert (claude_dir / "memory").is_dir()
        # Manifest written
        manifest_path = claude_dir / "memory-schema-manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["package"] == "memory-schema"
        assert "deployed_at" in manifest
        assert len(manifest["files_created"]) > 0
        # Hook registered in settings
        settings = json.loads((claude_dir / "settings.json").read_text())
        assert any(
            e.get("matcher") == "Write|Edit"
            for e in settings.get("hooks", {}).get("PostToolUse", [])
        )

    def test_deploy_creates_stop_hook(self, runner, tmp_path, plugin_dir):
        result, claude_dir = self._deploy(runner, tmp_path, plugin_dir)
        assert result.exit_code == 0
        settings = json.loads((claude_dir / "settings.json").read_text())
        stop_hooks = settings.get("hooks", {}).get("Stop", [])
        assert len(stop_hooks) == 1
        assert "stop.sh" in stop_hooks[0]["hooks"][0]["command"]

    def test_deploy_force_overwrites(self, runner, tmp_path, plugin_dir):
        # First deploy
        self._deploy(runner, tmp_path, plugin_dir)
        # Second deploy with --force
        result, claude_dir = self._deploy(runner, tmp_path, plugin_dir, force=True)
        assert result.exit_code == 0
        assert "Overwrite" in result.output
        manifest = json.loads((claude_dir / "memory-schema-manifest.json").read_text())
        assert len(manifest["files_overwritten"]) > 0

    def test_deploy_without_force_skips(self, runner, tmp_path, plugin_dir):
        # First deploy
        self._deploy(runner, tmp_path, plugin_dir)
        # Second deploy without --force
        result, claude_dir = self._deploy(runner, tmp_path, plugin_dir, force=False)
        assert result.exit_code == 0
        assert "Exists (skip)" in result.output

    def test_deploy_idempotent_hook(self, runner, tmp_path, plugin_dir):
        # First deploy registers hook
        self._deploy(runner, tmp_path, plugin_dir)
        # Second deploy detects existing hook
        result, claude_dir = self._deploy(runner, tmp_path, plugin_dir, force=True)
        assert "already registered" in result.output
        manifest = json.loads((claude_dir / "memory-schema-manifest.json").read_text())
        assert manifest["hook_was_existing"] is True

    def test_deploy_plugin_dir_not_found(self, runner, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", claude_dir / "manifest.json"), \
             patch("memoryschema.cli.plugin_cmd._find_plugin_dir", return_value=None):
            result = runner.invoke(cli, ["plugin", "deploy"])
        assert result.exit_code != 0

    def test_deploy_hook_script_missing(self, runner, tmp_path, plugin_dir):
        result, claude_dir = self._deploy(runner, tmp_path, plugin_dir, hook_path=None)
        assert result.exit_code == 0
        assert "script not found" in result.output.lower() or "register manually" in result.output.lower()


# ---------------------------------------------------------------------------
# 3. Uninstall command tests
# ---------------------------------------------------------------------------

class TestUninstall:
    def _deploy_then_uninstall(self, runner, tmp_path, plugin_dir, uninstall_args=None):
        """Deploy first, then run uninstall with given args."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        manifest_path = claude_dir / "memory-schema-manifest.json"

        # Deploy
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path), \
             patch("memoryschema.cli.plugin_cmd._find_plugin_dir", return_value=plugin_dir), \
             patch("memoryschema.cli.plugin_cmd._find_hook_script", return_value="/pkg/memoryschema/hook.sh"), \
             patch("memoryschema.cli.plugin_cmd._find_stop_hook_script", return_value="/pkg/memoryschema/stop.sh"):
            runner.invoke(cli, ["plugin", "deploy"], catch_exceptions=False)

        # Uninstall
        args = ["plugin", "uninstall"] + (uninstall_args or [])
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            result = runner.invoke(cli, args, catch_exceptions=False)
        return result, claude_dir

    def test_dry_run(self, runner, tmp_path, plugin_dir):
        """Without --confirm, shows what would be removed but doesn't delete."""
        result, claude_dir = self._deploy_then_uninstall(runner, tmp_path, plugin_dir)
        assert result.exit_code == 0
        assert "Dry run" in result.output
        # Files still exist
        for _, dst_rel in SKILL_FILES:
            assert (claude_dir / dst_rel).exists()

    def test_full_uninstall(self, runner, tmp_path, plugin_dir):
        """With --confirm, removes deployed files and manifest."""
        result, claude_dir = self._deploy_then_uninstall(
            runner, tmp_path, plugin_dir, ["--confirm"])
        assert result.exit_code == 0
        assert "Removed" in result.output
        # Manifest removed
        assert not (claude_dir / "memory-schema-manifest.json").exists()
        # Deployed skill files removed
        for _, dst_rel in SKILL_FILES:
            assert not (claude_dir / dst_rel).exists()

    def test_keep_data(self, runner, tmp_path, plugin_dir):
        """With --keep-data, preserves memory directory."""
        # Deploy first
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        manifest_path = claude_dir / "memory-schema-manifest.json"
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path), \
             patch("memoryschema.cli.plugin_cmd._find_plugin_dir", return_value=plugin_dir), \
             patch("memoryschema.cli.plugin_cmd._find_hook_script", return_value="/pkg/memoryschema/hook.sh"), \
             patch("memoryschema.cli.plugin_cmd._find_stop_hook_script", return_value="/pkg/memoryschema/stop.sh"):
            runner.invoke(cli, ["plugin", "deploy"], catch_exceptions=False)

        # Create a file in memory dir to verify it's preserved
        memory_dir = claude_dir / "memory"
        (memory_dir / "test-entity.md").write_text("test data")

        # Uninstall with --keep-data
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            result = runner.invoke(cli, ["plugin", "uninstall", "--confirm", "--keep-data"],
                                   catch_exceptions=False)
        assert result.exit_code == 0
        assert "Data preserved" in result.output
        assert memory_dir.exists()
        assert (memory_dir / "test-entity.md").exists()

    def test_no_manifest(self, runner, tmp_path):
        """No manifest means nothing to uninstall."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        manifest_path = claude_dir / "manifest.json"
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            result = runner.invoke(cli, ["plugin", "uninstall", "--confirm"],
                                   catch_exceptions=False)
        assert result.exit_code == 0
        assert "Nothing to uninstall" in result.output

    def test_hook_preservation_when_preexisting(self, runner, tmp_path, plugin_dir):
        """When hook_was_existing=True, uninstall does NOT remove the hook."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        manifest_path = claude_dir / "memory-schema-manifest.json"

        # Pre-register a hook before deploy
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps({
            "hooks": {"PostToolUse": [{"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "bash /pkg/memoryschema/hook.sh"}
            ]}]}
        }))

        # Deploy (hook already exists → hook_was_existing=True)
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path), \
             patch("memoryschema.cli.plugin_cmd._find_plugin_dir", return_value=plugin_dir), \
             patch("memoryschema.cli.plugin_cmd._find_hook_script", return_value="/pkg/memoryschema/hook.sh"), \
             patch("memoryschema.cli.plugin_cmd._find_stop_hook_script", return_value="/pkg/memoryschema/stop.sh"):
            runner.invoke(cli, ["plugin", "deploy", "--force"], catch_exceptions=False)

        # Verify manifest has hook_was_existing=True
        manifest = json.loads(manifest_path.read_text())
        assert manifest["hook_was_existing"] is True

        # Uninstall
        with patch("memoryschema.cli.plugin_cmd.CLAUDE_DIR", claude_dir), \
             patch("memoryschema.cli.plugin_cmd.MANIFEST_PATH", manifest_path):
            result = runner.invoke(cli, ["plugin", "uninstall", "--confirm"],
                                   catch_exceptions=False)
        assert result.exit_code == 0
        # Hook should NOT be removed (was pre-existing)
        assert "Unhooked" not in result.output
        settings = json.loads(settings_path.read_text())
        assert len(settings["hooks"]["PostToolUse"]) > 0
