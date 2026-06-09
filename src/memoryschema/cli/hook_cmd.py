"""PostToolUse hook management."""

import json
import os
import sys
from importlib.resources import files
from pathlib import Path

import click


def _settings_path():
    """Path to Claude Code global settings."""
    return Path.home() / ".claude" / "settings.json"


def _hook_script_path():
    """Resolve the installed hook script path."""
    try:
        return str(files("memoryschema.hooks") / "hook-post-write.sh")
    except Exception:
        return None


@click.group()
def hook():
    """Manage PostToolUse Write hook for Claude Code.

    Commands: install, uninstall, status, test.
    """
    pass


@hook.command()
@click.option("--timeout", default=10, type=int, help="Hook timeout in seconds. Default: 10.")
@click.pass_obj
def install(config, timeout):
    """Add PostToolUse Write hook to ~/.claude/settings.json.

    Registers the memory indexing hook that fires on every Write
    to memory/*.md files.

    Example:
        memoryschema hook install
        memoryschema hook install --timeout 15
    """
    hook_path = _hook_script_path()
    if not hook_path or not os.path.exists(hook_path):
        click.echo("Error: Hook script not found in package.", err=True)
        click.echo("Fix: Reinstall with 'pip install memory-schema'.", err=True)
        sys.exit(1)

    settings_file = _settings_path()
    settings = {}
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    post_tool = hooks.setdefault("PostToolUse", [])

    # Check if already registered
    hook_cmd = f"bash {hook_path}"
    for entry in post_tool:
        if entry.get("matcher") == "Write":
            for h in entry.get("hooks", []):
                if hook_path in h.get("command", ""):
                    click.echo(f"Hook already registered at {settings_file}")
                    return

    # Add new hook entry
    post_tool.append({
        "matcher": "Write",
        "hooks": [{
            "type": "command",
            "command": hook_cmd,
            "timeout": timeout,
        }]
    })

    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    click.echo(f"Registered PostToolUse Write hook.")
    click.echo(f"  Settings: {settings_file}")
    click.echo(f"  Script:   {hook_path}")
    click.echo(f"  Timeout:  {timeout}s")


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
        if entry.get("matcher") == "Write":
            new_hooks = [h for h in entry.get("hooks", [])
                        if hook_path and hook_path not in h.get("command", "")]
            if len(new_hooks) < len(entry.get("hooks", [])):
                removed = True
            if new_hooks:
                entry["hooks"] = new_hooks
                new_post_tool.append(entry)
        else:
            new_post_tool.append(entry)

    if removed:
        settings["hooks"]["PostToolUse"] = new_post_tool
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        click.echo("Hook unregistered.")
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

    post_tool = settings.get("hooks", {}).get("PostToolUse", [])
    registered = False
    for entry in post_tool:
        if entry.get("matcher") == "Write":
            for h in entry.get("hooks", []):
                if hook_path and hook_path in h.get("command", ""):
                    registered = True
                    click.echo(f"Registered: yes")
                    click.echo(f"  Timeout: {h.get('timeout', '?')}s")
                    return

    click.echo(f"Registered: no")
    click.echo(f"Fix: Run 'memoryschema hook install'")


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
            parts = [memory.get('description', '')]
            parts.extend(memory.get('observations', []))
            if memory.get('prompt'):
                parts.append(memory['prompt'])
            if memory.get('reasoning'):
                parts.append(memory['reasoning'])
            memory['embedding'] = embed_text(' '.join(parts), config=config)
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
