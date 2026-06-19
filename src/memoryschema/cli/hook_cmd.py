"""PostToolUse and Stop hook management."""

import json
import os
import sys
from importlib.resources import files
from pathlib import Path

import click


def _settings_path(per_project=False, project_root=None):
    """Path to Claude Code settings file.

    Args:
        per_project: If True, use project-level .claude/settings.json.
        project_root: Project root directory (required if per_project).
    """
    if per_project and project_root:
        return Path(project_root) / ".claude" / "settings.json"
    return Path.home() / ".claude" / "settings.json"


def _hook_script_path():
    """Resolve the installed PostToolUse hook script path."""
    try:
        return str(files("memoryschema.hooks") / "hook-post-write.sh")
    except Exception:
        return None


def _stop_hook_script_path():
    """Resolve the installed Stop hook script path."""
    try:
        return str(files("memoryschema.hooks") / "hook-stop.sh")
    except Exception:
        return None


@click.group()
def hook():
    """Manage PostToolUse and Stop hooks for Claude Code.

    Commands: install, uninstall, status, test.
    """
    pass


@hook.command()
@click.option("--timeout", default=10, type=int, help="Hook timeout in seconds. Default: 10.")
@click.option("--per-project", is_flag=True, help="Install to project-level .claude/settings.json instead of global.")
@click.pass_obj
def install(config, timeout, per_project):
    """Add PostToolUse Write hook to settings.json.

    By default installs to ~/.claude/settings.json (global).
    Use --per-project to install to the project's .claude/settings.json.

    Example:
        memoryschema hook install
        memoryschema hook install --per-project
        memoryschema hook install --timeout 15
    """
    hook_path = _hook_script_path()
    if not hook_path or not os.path.exists(hook_path):
        click.echo("Error: Hook script not found in package.", err=True)
        click.echo("Fix: Reinstall with 'pip install memory-schema'.", err=True)
        sys.exit(1)

    settings_file = _settings_path(
        per_project=per_project,
        project_root=config.project_root if per_project else None,
    )
    settings = {}
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    post_tool = hooks.setdefault("PostToolUse", [])

    # Check if already registered
    hook_cmd = f"bash {hook_path}"
    for entry in post_tool:
        if entry.get("matcher") in ("Write", "Write|Edit"):
            for h in entry.get("hooks", []):
                if hook_path in h.get("command", ""):
                    click.echo(f"Hook already registered at {settings_file}")
                    return

    # Add new hook entry
    post_tool.append({
        "matcher": "Write|Edit",
        "hooks": [{
            "type": "command",
            "command": hook_cmd,
            "timeout": timeout,
        }]
    })

    # Register Stop hook for chain update reminders
    stop_path = _stop_hook_script_path()
    if stop_path and os.path.exists(stop_path):
        stop_hooks = hooks.setdefault("Stop", [])
        stop_already = False
        for entry in stop_hooks:
            for h in entry.get("hooks", []):
                if stop_path in h.get("command", ""):
                    stop_already = True
                    break
        if not stop_already:
            stop_hooks.append({
                "hooks": [{
                    "type": "command",
                    "command": f"bash {stop_path}",
                    "timeout": 5,
                }]
            })

    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    click.echo(f"Registered PostToolUse Write|Edit hook.")
    click.echo(f"  Settings: {settings_file}")
    click.echo(f"  Script:   {hook_path}")
    click.echo(f"  Timeout:  {timeout}s")
    if stop_path and os.path.exists(stop_path):
        click.echo(f"Registered Stop hook.")
        click.echo(f"  Script:   {stop_path}")


@hook.command()
def uninstall():
    """Remove memory-schema hook from ~/.claude/settings.json.

    Example:
        memoryschema hook uninstall
    """
    settings_file = _settings_path()
    if not settings_file.exists():
        click.echo("No settings file found.")
        return

    with open(settings_file) as f:
        settings = json.load(f)

    post_tool = settings.get("hooks", {}).get("PostToolUse", [])
    hook_path = _hook_script_path()

    new_post_tool = []
    removed = False
    for entry in post_tool:
        if entry.get("matcher") in ("Write", "Write|Edit"):
            new_hooks = [h for h in entry.get("hooks", [])
                        if hook_path and hook_path not in h.get("command", "")]
            if len(new_hooks) < len(entry.get("hooks", [])):
                removed = True
            if new_hooks:
                entry["hooks"] = new_hooks
                new_post_tool.append(entry)
        else:
            new_post_tool.append(entry)

    # Also remove Stop hook entries
    stop_path = _stop_hook_script_path()
    stop_hooks = settings.get("hooks", {}).get("Stop", [])
    new_stop = []
    stop_removed = False
    for entry in stop_hooks:
        keep_hooks = [h for h in entry.get("hooks", [])
                      if stop_path and stop_path not in h.get("command", "")]
        if len(keep_hooks) < len(entry.get("hooks", [])):
            stop_removed = True
        if keep_hooks:
            entry["hooks"] = keep_hooks
            new_stop.append(entry)
        elif not entry.get("hooks"):
            new_stop.append(entry)

    if removed or stop_removed:
        settings["hooks"]["PostToolUse"] = new_post_tool
        if stop_removed:
            settings["hooks"]["Stop"] = new_stop
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        if removed:
            click.echo("PostToolUse hook unregistered.")
        if stop_removed:
            click.echo("Stop hook unregistered.")
    else:
        click.echo("Hook not found in settings.")


@hook.command("status")
def hook_status():
    """Show hook registration status.

    Example:
        memoryschema hook status
    """
    hook_path = _hook_script_path()
    click.echo(f"Hook script: {hook_path or 'not found'}")
    click.echo(f"Script exists: {os.path.exists(hook_path) if hook_path else False}")

    settings_file = _settings_path()
    if not settings_file.exists():
        click.echo(f"Settings: {settings_file} (not found)")
        return

    with open(settings_file) as f:
        settings = json.load(f)

    # Check PostToolUse hook
    post_tool = settings.get("hooks", {}).get("PostToolUse", [])
    post_registered = False
    for entry in post_tool:
        if entry.get("matcher") in ("Write", "Write|Edit"):
            for h in entry.get("hooks", []):
                if hook_path and hook_path in h.get("command", ""):
                    post_registered = True
                    click.echo(f"PostToolUse: yes (timeout: {h.get('timeout', '?')}s)")
                    break
            if post_registered:
                break
    if not post_registered:
        click.echo(f"PostToolUse: no")
        click.echo(f"  Fix: Run 'memoryschema hook install'")

    # Check Stop hook
    stop_path = _stop_hook_script_path()
    stop_hooks = settings.get("hooks", {}).get("Stop", [])
    stop_registered = False
    for entry in stop_hooks:
        for h in entry.get("hooks", []):
            if stop_path and stop_path in h.get("command", ""):
                stop_registered = True
                click.echo(f"Stop: yes (timeout: {h.get('timeout', '?')}s)")
                break
        if stop_registered:
            break
    if not stop_registered:
        click.echo(f"Stop: no")
        click.echo(f"  Fix: Run 'memoryschema hook install'")


@hook.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_obj
def test(config, file_path):
    """Simulate hook execution on a memory file.

    Parses, validates, optionally embeds, and indexes — same as the
    PostToolUse hook but invoked manually.

    Example:
        memoryschema hook test memory/my-memory.md
    """
    from memoryschema.tags import parse_memory_file
    from memoryschema.validator import validate

    # Parse
    memory = parse_memory_file(file_path)
    if memory is None:
        click.echo(f"Error: Failed to parse {file_path}.", err=True)
        sys.exit(1)
    click.echo(f"Parsed: {memory['name']} — {memory.get('description', '')[:80]}")

    # Validate
    with open(file_path) as f:
        content = f.read()
    errors = validate(content, file_path)
    if errors:
        click.echo(f"Validation errors:")
        for rule, msg in errors:
            click.echo(f"  [{rule}] {msg}")
    else:
        click.echo(f"Validation: passed")

    # Embed
    if config.voyage_api_key:
        try:
            from memoryschema.embeddings import embed_text
            from memoryschema.embedding_input import compose_embedding_text
            text = compose_embedding_text(memory)
            memory['embedding'] = embed_text(text, config=config)
            click.echo(f"Embedded: {len(memory['embedding'])} dimensions")
        except Exception as e:
            click.echo(f"Embedding: skipped ({e})")
    else:
        click.echo("Embedding: skipped (VOYAGE_API_KEY not set)")

    # Index
    from memoryschema.store import get_store
    store = get_store(config=config)
    store.upsert(memory)
    click.echo(f"Indexed: {memory['name']}")
