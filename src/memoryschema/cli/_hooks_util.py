"""Shared hook management utilities for PostToolUse and Stop hooks.

Used by hook_cmd.py (memoryschema hook) and plugin_cmd.py (memoryschema plugin).
Single source of truth for hook registration, detection, removal, inspection,
upgrade, and diagnostics.
"""

import json
import os
import re
import shutil
import subprocess
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

HOOK_VERSION = "2"
"""Current hook version. v0=not installed, v1=Write only, v2=Write|Edit+Stop."""


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


# --- Inspection and diagnostics ---

def get_hook_registration_detail(settings, hook_script_path=None, stop_script_path=None):
    """Inspect hook registration state in detail.

    Args:
        settings: Parsed settings.json dict.
        hook_script_path: Expected PostToolUse hook script path (for existence check).
        stop_script_path: Expected Stop hook script path (for existence check).

    Returns:
        dict with keys: post_tool_use_registered, post_tool_use_matcher,
        post_tool_use_command, post_tool_use_timeout, post_tool_use_stale,
        post_tool_use_script_exists, post_tool_use_script_executable,
        stop_registered, stop_command, stop_timeout, stop_script_exists,
        stop_script_executable, needs_upgrade, upgrade_reasons.
    """
    detail = {
        "post_tool_use_registered": False,
        "post_tool_use_matcher": None,
        "post_tool_use_command": None,
        "post_tool_use_timeout": None,
        "post_tool_use_stale": False,
        "post_tool_use_script_exists": None,
        "post_tool_use_script_executable": None,
        "stop_registered": False,
        "stop_command": None,
        "stop_timeout": None,
        "stop_script_exists": None,
        "stop_script_executable": None,
        "needs_upgrade": False,
        "upgrade_reasons": [],
    }

    hooks = settings.get("hooks", {})

    # Check PostToolUse
    for entry in hooks.get("PostToolUse", []):
        if entry.get("matcher") in LEGACY_MATCHERS:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if "memoryschema" in cmd or "hook-post-write" in cmd:
                    detail["post_tool_use_registered"] = True
                    detail["post_tool_use_matcher"] = entry.get("matcher")
                    detail["post_tool_use_command"] = cmd
                    detail["post_tool_use_timeout"] = h.get("timeout")
                    detail["post_tool_use_stale"] = entry.get("matcher") == "Write"
                    # Check script from command
                    script = _extract_script_path(cmd)
                    if script:
                        detail["post_tool_use_script_exists"] = os.path.exists(script)
                        detail["post_tool_use_script_executable"] = os.access(script, os.X_OK) if os.path.exists(script) else False
                    elif hook_script_path:
                        detail["post_tool_use_script_exists"] = os.path.exists(hook_script_path)
                        detail["post_tool_use_script_executable"] = os.access(hook_script_path, os.X_OK) if os.path.exists(hook_script_path) else False
                    break
            if detail["post_tool_use_registered"]:
                break

    # Check Stop
    for entry in hooks.get("Stop", []):
        for h in entry.get("hooks", []):
            cmd = h.get("command", "")
            if "hook-stop" in cmd:
                detail["stop_registered"] = True
                detail["stop_command"] = cmd
                detail["stop_timeout"] = h.get("timeout")
                script = _extract_script_path(cmd)
                if script:
                    detail["stop_script_exists"] = os.path.exists(script)
                    detail["stop_script_executable"] = os.access(script, os.X_OK) if os.path.exists(script) else False
                elif stop_script_path:
                    detail["stop_script_exists"] = os.path.exists(stop_script_path)
                    detail["stop_script_executable"] = os.access(stop_script_path, os.X_OK) if os.path.exists(stop_script_path) else False
                break
        if detail["stop_registered"]:
            break

    # Determine upgrade needs
    reasons = []
    if detail["post_tool_use_stale"]:
        reasons.append('PostToolUse matcher is "Write" (should be "Write|Edit")')
    if detail["post_tool_use_registered"] and not detail["stop_registered"]:
        reasons.append("Stop hook is not registered")
    if reasons:
        detail["needs_upgrade"] = True
        detail["upgrade_reasons"] = reasons

    return detail


def _extract_script_path(command):
    """Extract the script path from a hook command string like 'bash /path/to/script.sh'."""
    parts = command.strip().split()
    if len(parts) >= 2 and parts[0] == "bash":
        return parts[1]
    return None


def detect_hook_version(detail):
    """Determine hook version from registration detail.

    Args:
        detail: Dict from get_hook_registration_detail().

    Returns:
        str: "0" (not installed), "1" (Write only), or "2" (Write|Edit + Stop).
    """
    if not detail["post_tool_use_registered"]:
        return "0"
    if detail["post_tool_use_stale"] or not detail["stop_registered"]:
        return "1"
    return "2"


def upgrade_hooks(settings, hook_script_path, stop_script_path):
    """In-place upgrade of hook registration to current version.

    1. Changes "Write" matcher to "Write|Edit" for memoryschema PostToolUse hooks.
    2. Adds Stop hook entry if missing.

    Args:
        settings: Parsed settings.json dict (modified in place).
        hook_script_path: Path to hook-post-write.sh (for reference).
        stop_script_path: Path to hook-stop.sh (for adding Stop entry).

    Returns:
        list[str]: Descriptions of changes made (empty if already current).
    """
    changes = []
    hooks = settings.get("hooks", {})

    # Upgrade PostToolUse matcher
    for entry in hooks.get("PostToolUse", []):
        if entry.get("matcher") == "Write":
            for h in entry.get("hooks", []):
                if "memoryschema" in h.get("command", "") or "hook-post-write" in h.get("command", ""):
                    entry["matcher"] = HOOK_MATCHER
                    changes.append(f'PostToolUse matcher: "Write" → "{HOOK_MATCHER}"')
                    break

    # Add Stop hook if missing
    stop_found = False
    for entry in hooks.get("Stop", []):
        for h in entry.get("hooks", []):
            if "hook-stop" in h.get("command", ""):
                stop_found = True
                break
        if stop_found:
            break

    if not stop_found and stop_script_path:
        if "Stop" not in hooks:
            hooks["Stop"] = []
            settings["hooks"] = hooks
        hooks["Stop"].append({
            "hooks": [{
                "type": "command",
                "command": f"bash {stop_script_path}",
                "timeout": STOP_HOOK_TIMEOUT,
            }],
        })
        changes.append(f"Stop hook: added (bash {stop_script_path})")

    return changes


def find_project_settings(scan_dirs=None):
    """Find all .claude/settings.json files across projects.

    Always includes the global ~/.claude/settings.json. Then scans
    common project directories for per-project settings.

    Args:
        scan_dirs: List of directories to scan. If None, uses defaults.

    Returns:
        list[dict]: Each with keys: path, project_root, project_name, scope.
    """
    results = []
    seen = set()

    # Always include global
    global_path = get_settings_path()
    if global_path.exists():
        results.append({
            "path": str(global_path),
            "project_root": str(Path.home() / ".claude"),
            "project_name": "(global)",
            "scope": "global",
        })
        seen.add(str(global_path.resolve()))

    # Scan directories
    if scan_dirs is None:
        home = Path.home()
        scan_dirs = [
            home / "Projects", home / "Developer", home / "Code",
            home / "repos", home / "src", Path.cwd(),
        ]

    for scan_dir in scan_dirs:
        scan_dir = Path(scan_dir)
        if not scan_dir.exists():
            continue
        # Walk depth 3: scan_dir/project/.claude/settings.json
        for project_dir in scan_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            settings_path = project_dir / ".claude" / "settings.json"
            if settings_path.exists() and str(settings_path.resolve()) not in seen:
                results.append({
                    "path": str(settings_path),
                    "project_root": str(project_dir),
                    "project_name": project_dir.name,
                    "scope": "project",
                })
                seen.add(str(settings_path.resolve()))

    return results


def validate_hook_python(hook_script_path, hook_command=None):
    """Validate the Python interpreter referenced by a hook script or command.

    Checks (in order):
    1. MEMORYSCHEMA_PYTHON default in the script
    2. PYTHON= assignment in the script
    3. Python path argument in the settings.json command string

    Args:
        hook_script_path: Path to the hook shell script.
        hook_command: Full command string from settings.json (e.g. "bash /path/hook.sh /path/python3").

    Returns:
        tuple[bool, str]: (valid, detail_message).
    """
    if not hook_script_path or not os.path.exists(hook_script_path):
        return False, "Hook script not found"

    # Extract Python path from script
    python_path = None
    try:
        with open(hook_script_path) as f:
            for line in f:
                match = re.search(r'MEMORYSCHEMA_PYTHON:-([^}]+)', line)
                if match:
                    python_path = match.group(1).strip()
                    break
                match = re.search(r'^PYTHON="?([^"}\n]+)"?', line)
                if match:
                    python_path = match.group(1).strip()
                    break
    except Exception as e:
        return False, f"Cannot read script: {e}"

    # Fallback: extract from settings.json command args
    if not python_path and hook_command:
        parts = hook_command.split()
        # Command format: "bash /path/hook.sh /path/python3"
        if len(parts) >= 3:
            candidate = parts[-1]
            if os.path.exists(candidate):
                python_path = candidate

    if not python_path:
        return False, "No Python interpreter found in script or command"

    if not os.path.exists(python_path):
        return False, f"Python not found: {python_path}"

    # Check memoryschema import
    try:
        result = subprocess.run(
            [python_path, "-c", "import memoryschema"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return True, f"OK ({python_path})"
        return False, f"import memoryschema failed: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Python import check timed out ({python_path})"
    except Exception as e:
        return False, f"Cannot run Python: {e}"


def dry_run_post_tool_use_hook(hook_script_path):
    """Run PostToolUse hook with synthetic input (no side effects).

    Pipes a Write event for a non-existent memory path. The hook should
    exit 0 (file doesn't exist, silently skipped after path filter).

    Args:
        hook_script_path: Path to hook-post-write.sh.

    Returns:
        tuple[bool, str, int]: (success, output, exit_code).
    """
    if not hook_script_path or not os.path.exists(hook_script_path):
        return False, "Hook script not found", -1

    test_input = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/memoryschema-dry-run/memory/dry-run.md"},
    })
    try:
        result = subprocess.run(
            ["bash", hook_script_path],
            input=test_input, capture_output=True, text=True, timeout=10,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output, result.returncode
    except subprocess.TimeoutExpired:
        return False, "Hook timed out (10s)", -1
    except Exception as e:
        return False, str(e), -1


def dry_run_stop_hook(stop_script_path):
    """Run Stop hook and validate JSON output.

    Pipes empty JSON. Expects valid JSON output (either {} or a systemMessage).

    Args:
        stop_script_path: Path to hook-stop.sh.

    Returns:
        tuple[bool, str, int]: (success, output, exit_code).
    """
    if not stop_script_path or not os.path.exists(stop_script_path):
        return False, "Stop hook script not found", -1

    try:
        result = subprocess.run(
            ["bash", stop_script_path],
            input="{}", capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.strip()
        # Validate JSON output
        if output:
            try:
                json.loads(output)
            except json.JSONDecodeError:
                return False, f"Invalid JSON output: {output}", result.returncode
        return result.returncode == 0, output or "{}", result.returncode
    except subprocess.TimeoutExpired:
        return False, "Stop hook timed out (5s)", -1
    except Exception as e:
        return False, str(e), -1
