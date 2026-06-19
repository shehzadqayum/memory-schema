"""PostToolUse and Stop hook management."""

import os
import sys

import click

from memoryschema.cli._hooks_util import (
    HOOK_MATCHER,
    LEGACY_MATCHERS,
    find_hook_script_path,
    find_stop_hook_script_path,
    get_settings_path,
    hook_already_registered,
    read_settings,
    register_hooks,
    unregister_hooks,
    write_settings,
)


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
    """Add PostToolUse and Stop hooks to settings.json.

    By default installs to ~/.claude/settings.json (global).
    Use --per-project to install to the project's .claude/settings.json.

    Example:
        memoryschema hook install
        memoryschema hook install --per-project
        memoryschema hook install --timeout 15
    """
    hook_path = find_hook_script_path()
    if not hook_path or not os.path.exists(hook_path):
        click.echo("Error: Hook script not found in package.", err=True)
        click.echo("Fix: Reinstall with 'pip install memory-schema'.", err=True)
        sys.exit(1)

    settings_file = get_settings_path(
        per_project=per_project,
        project_root=config.project_root if per_project else None,
    )
    settings = read_settings(settings_file)

    # Check if already registered
    registered, existing_cmd = hook_already_registered(settings)
    if registered and hook_path in existing_cmd:
        click.echo(f"Hook already registered at {settings_file}")
        return

    # Register both hooks
    stop_path = find_stop_hook_script_path()
    hook_cmd = f"bash {hook_path}"
    stop_cmd = f"bash {stop_path}" if stop_path and os.path.exists(stop_path) else None
    register_hooks(settings, hook_cmd, stop_cmd)

    write_settings(settings_file, settings, backup=True)

    click.echo(f"Registered PostToolUse {HOOK_MATCHER} hook.")
    click.echo(f"  Settings: {settings_file}")
    click.echo(f"  Script:   {hook_path}")
    click.echo(f"  Timeout:  {timeout}s")
    if stop_cmd:
        click.echo(f"Registered Stop hook.")
        click.echo(f"  Script:   {stop_path}")


@hook.command()
def uninstall():
    """Remove memory-schema hooks from ~/.claude/settings.json.

    Example:
        memoryschema hook uninstall
    """
    settings_file = get_settings_path()
    if not settings_file.exists():
        click.echo("No settings file found.")
        return

    settings = read_settings(settings_file)
    settings, removed = unregister_hooks(settings)

    if removed:
        write_settings(settings_file, settings, backup=True)
        for cmd in removed:
            if "hook-stop" in cmd:
                click.echo("Stop hook unregistered.")
            else:
                click.echo("PostToolUse hook unregistered.")
    else:
        click.echo("Hook not found in settings.")


@hook.command("status")
def hook_status():
    """Show hook registration status.

    Example:
        memoryschema hook status
    """
    hook_path = find_hook_script_path()
    click.echo(f"Hook script: {hook_path or 'not found'}")
    click.echo(f"Script exists: {os.path.exists(hook_path) if hook_path else False}")

    settings_file = get_settings_path()
    if not settings_file.exists():
        click.echo(f"Settings: {settings_file} (not found)")
        return

    settings = read_settings(settings_file)

    # Check PostToolUse hook
    post_registered = False
    for entry in settings.get("hooks", {}).get("PostToolUse", []):
        if entry.get("matcher") in LEGACY_MATCHERS:
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
    stop_path = find_stop_hook_script_path()
    stop_registered = False
    for entry in settings.get("hooks", {}).get("Stop", []):
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
