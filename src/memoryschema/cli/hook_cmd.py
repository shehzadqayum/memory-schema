"""PostToolUse and Stop hook management."""

import json as json_mod
import os
import sys

import click

from memoryschema.cli._hooks_util import (
    HOOK_MATCHER,
    HOOK_VERSION,
    LEGACY_MATCHERS,
    detect_hook_version,
    dry_run_post_tool_use_hook,
    dry_run_stop_hook,
    find_hook_script_path,
    find_project_settings,
    find_stop_hook_script_path,
    get_hook_registration_detail,
    get_settings_path,
    hook_already_registered,
    read_settings,
    register_hooks,
    unregister_hooks,
    upgrade_hooks,
    validate_hook_python,
    write_settings,
)


@click.group()
def hook():
    """Manage PostToolUse and Stop hooks for Claude Code.

    Commands: install, uninstall, status, upgrade, check, scan, test.
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
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output.")
def hook_status(as_json):
    """Show hook registration status with version and staleness info.

    Example:
        memoryschema hook status
        memoryschema hook status --json
    """
    hook_path = find_hook_script_path()
    stop_path = find_stop_hook_script_path()
    settings_file = get_settings_path()

    if not settings_file.exists():
        if as_json:
            click.echo(json_mod.dumps({"version": "0", "error": "settings not found"}))
        else:
            click.echo(f"Settings: {settings_file} (not found)")
        return

    settings = read_settings(settings_file)
    detail = get_hook_registration_detail(settings, hook_path, stop_path)
    version = detect_hook_version(detail)

    if as_json:
        detail["version"] = version
        click.echo(json_mod.dumps(detail, indent=2))
        return

    click.echo(f"Version:     v{version} (current: v{HOOK_VERSION})")

    # PostToolUse
    if detail["post_tool_use_registered"]:
        stale = " ⚠ STALE" if detail["post_tool_use_stale"] else ""
        click.echo(f"PostToolUse: yes (matcher: {detail['post_tool_use_matcher']}, timeout: {detail['post_tool_use_timeout']}s){stale}")
        if detail["post_tool_use_script_exists"] is not None:
            exists = "yes" if detail["post_tool_use_script_exists"] else "MISSING"
            click.echo(f"  Script:    {exists}")
    else:
        click.echo("PostToolUse: no")

    # Stop
    if detail["stop_registered"]:
        click.echo(f"Stop:        yes (timeout: {detail['stop_timeout']}s)")
        if detail["stop_script_exists"] is not None:
            exists = "yes" if detail["stop_script_exists"] else "MISSING"
            click.echo(f"  Script:    {exists}")
    else:
        click.echo("Stop:        no ⚠ MISSING")

    # Upgrade suggestion
    if detail["needs_upgrade"]:
        click.echo(f"\nNeeds upgrade:")
        for reason in detail["upgrade_reasons"]:
            click.echo(f"  - {reason}")
        click.echo(f"  Fix: Run 'memoryschema hook upgrade'")


@hook.command("upgrade")
@click.option("--per-project", is_flag=True, help="Upgrade project-level hooks.")
@click.option("--dry-run", is_flag=True, help="Show what would change without modifying.")
@click.pass_obj
def hook_upgrade(config, per_project, dry_run):
    """Upgrade hooks to current version (v2: Write|Edit + Stop).

    Fixes stale "Write" matchers and adds missing Stop hook.

    Example:
        memoryschema hook upgrade
        memoryschema hook upgrade --dry-run
        memoryschema hook upgrade --per-project
    """
    settings_file = get_settings_path(
        per_project=per_project,
        project_root=config.project_root if per_project else None,
    )
    if not settings_file.exists():
        click.echo(f"Settings not found: {settings_file}")
        return

    settings = read_settings(settings_file)
    hook_path = find_hook_script_path()
    stop_path = find_stop_hook_script_path()

    detail = get_hook_registration_detail(settings, hook_path, stop_path)
    version = detect_hook_version(detail)

    if not detail["needs_upgrade"]:
        click.echo(f"Already current (v{version}). No upgrade needed.")
        return

    click.echo(f"Current version: v{version}")
    click.echo(f"Target version:  v{HOOK_VERSION}")

    if dry_run:
        click.echo("\nWould apply:")
        for reason in detail["upgrade_reasons"]:
            click.echo(f"  - {reason}")
        click.echo("\nPass without --dry-run to apply.")
        return

    changes = upgrade_hooks(settings, hook_path, stop_path)
    write_settings(settings_file, settings, backup=True)

    click.echo("\nApplied:")
    for change in changes:
        click.echo(f"  ✓ {change}")
    click.echo(f"\nUpgraded to v{HOOK_VERSION}.")


@hook.command("check")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output.")
@click.pass_obj
def hook_check(config, as_json):
    """Run diagnostic checks on hook scripts and configuration.

    Tests script existence, executability, Python interpreter, and
    dry-run execution of both hooks.

    Example:
        memoryschema hook check
        memoryschema hook check --json
    """
    hook_path = find_hook_script_path()
    stop_path = find_stop_hook_script_path()
    checks = []

    def _check(name, fn):
        try:
            passed, detail = fn()
        except Exception as e:
            passed, detail = False, str(e)
        checks.append({"name": name, "passed": passed, "detail": detail})
        return passed

    # 1. PostToolUse script exists
    _check("post_tool_use_script_exists",
           lambda: (bool(hook_path and os.path.exists(hook_path)),
                    hook_path or "not found"))

    # 2. PostToolUse script executable
    _check("post_tool_use_script_executable",
           lambda: (bool(hook_path and os.access(hook_path, os.X_OK)),
                    "executable" if hook_path and os.access(hook_path, os.X_OK) else "not executable"))

    # 3. Python interpreter valid
    _check("python_interpreter",
           lambda: validate_hook_python(hook_path))

    # 4. PostToolUse dry run
    def _post_dry():
        ok, output, code = dry_run_post_tool_use_hook(hook_path)
        return ok, f"exit {code}: {output[:100]}" if output else f"exit {code}"
    _check("post_tool_use_dry_run", _post_dry)

    # 5. Stop script exists
    _check("stop_script_exists",
           lambda: (bool(stop_path and os.path.exists(stop_path)),
                    stop_path or "not found"))

    # 6. Stop script executable
    _check("stop_script_executable",
           lambda: (bool(stop_path and os.access(stop_path, os.X_OK)),
                    "executable" if stop_path and os.access(stop_path, os.X_OK) else "not executable"))

    # 7. Stop dry run
    def _stop_dry():
        ok, output, code = dry_run_stop_hook(stop_path)
        return ok, f"exit {code}: {output[:100]}" if output else f"exit {code}"
    _check("stop_dry_run", _stop_dry)

    # 8. Sentinel directory writable
    _check("sentinel_writable",
           lambda: (os.access("/tmp", os.W_OK), "/tmp is writable" if os.access("/tmp", os.W_OK) else "/tmp not writable"))

    if as_json:
        click.echo(json_mod.dumps(checks, indent=2))
        return

    passed_count = sum(1 for c in checks if c["passed"])
    for c in checks:
        icon = "✓" if c["passed"] else "✗"
        click.echo(f"  {icon} {c['name']}: {c['detail']}")
    click.echo(f"\n{passed_count}/{len(checks)} checks passed.")


@hook.command("scan")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output.")
@click.option("--scan-dir", multiple=True, help="Additional directories to scan.")
@click.pass_obj
def hook_scan(config, as_json, scan_dir):
    """Scan for hook installations across all projects.

    Finds global and per-project settings.json files, checks hook
    registration state, and reports version and staleness.

    Example:
        memoryschema hook scan
        memoryschema hook scan --scan-dir ~/Work
        memoryschema hook scan --json
    """
    from pathlib import Path
    scan_dirs = [Path(d) for d in scan_dir] if scan_dir else None
    results = find_project_settings(scan_dirs)

    hook_path = find_hook_script_path()
    stop_path = find_stop_hook_script_path()

    entries = []
    needs_upgrade = 0
    for r in results:
        settings = read_settings(r["path"])
        detail = get_hook_registration_detail(settings, hook_path, stop_path)
        version = detect_hook_version(detail)
        entry = {
            "scope": r["scope"],
            "project": r["project_name"],
            "path": r["path"],
            "version": version,
            "matcher": detail["post_tool_use_matcher"] or "-",
            "stop": "yes" if detail["stop_registered"] else "no",
            "needs_upgrade": detail["needs_upgrade"],
        }
        entries.append(entry)
        if detail["needs_upgrade"]:
            needs_upgrade += 1

    if as_json:
        click.echo(json_mod.dumps(entries, indent=2))
        return

    if not entries:
        click.echo("No hook installations found.")
        return

    # Table output
    click.echo(f"{'Scope':<10} {'Project':<25} {'Version':<8} {'Matcher':<12} {'Stop':<5} {'Status'}")
    click.echo("-" * 75)
    for e in entries:
        status = "⚠ UPGRADE" if e["needs_upgrade"] else "OK"
        click.echo(f"{e['scope']:<10} {e['project']:<25} v{e['version']:<7} {e['matcher']:<12} {e['stop']:<5} {status}")

    click.echo(f"\n{len(entries)} installation(s) found.")
    if needs_upgrade:
        click.echo(f"{needs_upgrade} need(s) upgrade. Run: memoryschema hook upgrade")


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
