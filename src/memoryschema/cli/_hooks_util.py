"""Shared hook management utilities for PostToolUse and Stop hooks.

Used by hook_cmd.py (memoryschema hook) and plugin_cmd.py (memoryschema plugin).
Single source of truth for hook registration, detection, and removal.
"""

import json
import shutil
from importlib.resources import files
from pathlib import Path


# --- Constants ---

HOOK_MATCHER = "Write|Edit"
"""The matcher string for new PostToolUse hook registrations."""

LEGACY_MATCHERS = ("Write", "Write|Edit")
"""Matchers to detect when checking/removing hooks (backward compat with pre-Edit installs)."""

POST_TOOL_USE_TIMEOUT = 10
"""Default timeout in seconds for PostToolUse hooks."""

STOP_HOOK_TIMEOUT = 5
"""Default timeout in seconds for Stop hooks."""


# --- Path resolution ---

def find_hook_script_path():
    """Resolve the installed PostToolUse hook script path.

    Tries importlib.resources first (pip-installed package), then falls back
    to a relative path from the package source (development mode).

    Returns:
        str or None: Absolute path to hook-post-write.sh, or None if not found.
    """
    try:
        hook_path = Path(str(files("memoryschema.hooks") / "hook-post-write.sh"))
        if hook_path.exists():
            return str(hook_path)
    except Exception:
        pass
    candidate = Path(__file__).resolve().parent.parent / "hooks" / "hook-post-write.sh"
    if candidate.exists():
        return str(candidate)
    return None


def find_stop_hook_script_path():
    """Resolve the installed Stop hook script path.

    Returns:
        str or None: Absolute path to hook-stop.sh, or None if not found.
    """
    try:
        hook_path = Path(str(files("memoryschema.hooks") / "hook-stop.sh"))
        if hook_path.exists():
            return str(hook_path)
    except Exception:
        pass
    candidate = Path(__file__).resolve().parent.parent / "hooks" / "hook-stop.sh"
    if candidate.exists():
        return str(candidate)
    return None


def get_settings_path(per_project=False, project_root=None):
    """Path to Claude Code settings file.

    Args:
        per_project: If True, use project-level .claude/settings.json.
        project_root: Project root directory (required if per_project).

    Returns:
        Path: settings.json path (global or project-level).
    """
    if per_project and project_root:
        return Path(project_root) / ".claude" / "settings.json"
    return Path.home() / ".claude" / "settings.json"


# --- Settings I/O ---

def read_settings(path=None):
    """Read Claude Code settings.json.

    Args:
        path: Explicit path to settings.json. If None, uses global default.

    Returns:
        dict: Parsed settings, or {} if file doesn't exist.
    """
    if path is None:
        path = get_settings_path()
    if Path(path).exists():
        with open(path) as f:
            return json.load(f)
    return {}


def write_settings(path, data, backup=True):
    """Write Claude Code settings.json with optional backup.

    Args:
        path: Path to settings.json.
        data: Settings dict to write.
        backup: If True and file exists, create .memory-schema-backup first.
    """
    path = Path(path)
    if backup and path.exists():
        backup_path = path.parent / "settings.json.memory-schema-backup"
        shutil.copy2(path, backup_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# --- Hook registration logic ---

def hook_already_registered(settings, fragment="memoryschema"):
    """Check if a memory-schema hook is already in PostToolUse.

    Checks both legacy "Write" and current "Write|Edit" matchers for
    backward compatibility.

    Args:
        settings: Parsed settings.json dict.
        fragment: Command string fragment to search for.

    Returns:
        tuple[bool, str | None]: (is_registered, command_string).
    """
    hooks = settings.get("hooks", {})
    for entry in hooks.get("PostToolUse", []):
        if entry.get("matcher") in LEGACY_MATCHERS:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if fragment in cmd:
                    return True, cmd
    return False, None


def register_hooks(settings, hook_cmd, stop_cmd=None):
    """Add PostToolUse Write|Edit and optional Stop hooks to settings.

    Args:
        settings: Parsed settings.json dict (modified in place).
        hook_cmd: Command string for the PostToolUse hook.
        stop_cmd: Command string for the Stop hook (optional).

    Returns:
        dict: The modified settings dict.
    """
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PostToolUse" not in settings["hooks"]:
        settings["hooks"]["PostToolUse"] = []
    settings["hooks"]["PostToolUse"].append({
        "matcher": HOOK_MATCHER,
        "hooks": [{
            "type": "command",
            "command": hook_cmd,
            "timeout": POST_TOOL_USE_TIMEOUT,
        }],
    })
    if stop_cmd:
        if "Stop" not in settings["hooks"]:
            settings["hooks"]["Stop"] = []
        settings["hooks"]["Stop"].append({
            "hooks": [{
                "type": "command",
                "command": stop_cmd,
                "timeout": STOP_HOOK_TIMEOUT,
            }],
        })
    return settings


def unregister_hooks(settings, fragment="memoryschema"):
    """Remove memory-schema PostToolUse and Stop hook entries from settings.

    Removes entries where the command contains the fragment string.
    Checks both legacy "Write" and current "Write|Edit" matchers.

    Args:
        settings: Parsed settings.json dict (modified in place).
        fragment: Command string fragment to match for removal.

    Returns:
        tuple[dict, list[str]]: (modified settings, list of removed command strings).
    """
    hooks = settings.get("hooks", {})
    removed = []

    # Remove PostToolUse entries
    post_tool = hooks.get("PostToolUse", [])
    filtered = []
    for entry in post_tool:
        if entry.get("matcher") in LEGACY_MATCHERS:
            keep_hooks = []
            for h in entry.get("hooks", []):
                if fragment in h.get("command", ""):
                    removed.append(h.get("command", ""))
                else:
                    keep_hooks.append(h)
            if keep_hooks:
                entry["hooks"] = keep_hooks
                filtered.append(entry)
        else:
            filtered.append(entry)
    if "PostToolUse" in hooks:
        settings["hooks"]["PostToolUse"] = filtered

    # Remove Stop hook entries
    stop_hooks = hooks.get("Stop", [])
    stop_filtered = []
    for entry in stop_hooks:
        keep_hooks = []
        for h in entry.get("hooks", []):
            if "hook-stop.sh" in h.get("command", ""):
                removed.append(h.get("command", ""))
            else:
                keep_hooks.append(h)
        if keep_hooks:
            entry["hooks"] = keep_hooks
            stop_filtered.append(entry)
    if "Stop" in hooks:
        settings["hooks"]["Stop"] = stop_filtered

    return settings, removed
