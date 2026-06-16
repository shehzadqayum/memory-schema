"""CLI commands for deploying/uninstalling the memory-schema plugin at user level (~/.claude/)."""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import click

from memoryschema._version import __version__


CLAUDE_DIR = Path.home() / ".claude"
MANIFEST_PATH = CLAUDE_DIR / "memory-schema-manifest.json"

# Files to deploy: (source relative to plugin dir, target relative to ~/.claude/)
SKILL_FILES = [
    ("skills/recall/SKILL.md", "skills/recall/SKILL.md"),
    ("skills/chain-start/SKILL.md", "skills/chain-start/SKILL.md"),
    ("skills/chain-status/SKILL.md", "skills/chain-status/SKILL.md"),
    ("skills/chain-release/SKILL.md", "skills/chain-release/SKILL.md"),
    ("skills/memory-status/SKILL.md", "skills/memory-status/SKILL.md"),
]

RULE_FILES = [
    ("rules/memory-schema.md", "rules/memory-schema.md"),
    ("rules/memory-working.md", "rules/memory-working.md"),
]


def _find_plugin_dir():
    """Find the .claude-plugin/ directory relative to the package source."""
    # Walk up from this file to find the repo root with .claude-plugin/
    pkg_dir = Path(__file__).resolve().parent.parent  # src/memoryschema/
    repo_root = pkg_dir.parent.parent  # repo root (contains src/ and .claude-plugin/)
    plugin_dir = repo_root / ".claude-plugin"
    if plugin_dir.is_dir():
        return plugin_dir
    # Fallback: try importlib.resources for installed package
    try:
        from importlib.resources import files as pkg_files
        candidate = Path(str(pkg_files("memoryschema"))) / ".." / ".." / ".claude-plugin"
        if candidate.resolve().is_dir():
            return candidate.resolve()
    except Exception:
        pass
    return None


def _find_hook_script():
    """Find the hook-post-write.sh script path."""
    try:
        from importlib.resources import files as pkg_files
        hook_path = Path(str(pkg_files("memoryschema.hooks") / "hook-post-write.sh"))
        if hook_path.exists():
            return str(hook_path)
    except Exception:
        pass
    # Fallback: relative to this file
    candidate = Path(__file__).resolve().parent.parent / "hooks" / "hook-post-write.sh"
    if candidate.exists():
        return str(candidate)
    return None


def _read_settings():
    """Read ~/.claude/settings.json."""
    settings_path = CLAUDE_DIR / "settings.json"
    if settings_path.exists():
        with open(settings_path) as f:
            return json.load(f)
    return {}


def _write_settings(data):
    """Write ~/.claude/settings.json."""
    settings_path = CLAUDE_DIR / "settings.json"
    # Backup before modifying
    if settings_path.exists():
        backup = CLAUDE_DIR / "settings.json.memory-schema-backup"
        shutil.copy2(settings_path, backup)
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _hook_already_registered(settings, hook_command_fragment="memoryschema"):
    """Check if a memory-schema hook is already in PostToolUse Write."""
    hooks = settings.get("hooks", {})
    for entry in hooks.get("PostToolUse", []):
        if entry.get("matcher") == "Write":
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if hook_command_fragment in cmd:
                    return True, cmd
    return False, None


def _add_hook(settings, hook_command):
    """Add the memory-schema PostToolUse Write hook to settings."""
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PostToolUse" not in settings["hooks"]:
        settings["hooks"]["PostToolUse"] = []
    settings["hooks"]["PostToolUse"].append({
        "matcher": "Write",
        "hooks": [{
            "type": "command",
            "command": hook_command,
            "timeout": 10,
        }],
    })
    return settings


def _remove_hook(settings, hook_command_fragment="memoryschema"):
    """Remove memory-schema PostToolUse Write hook entries from settings."""
    hooks = settings.get("hooks", {})
    post_tool = hooks.get("PostToolUse", [])
    filtered = []
    removed = []
    for entry in post_tool:
        if entry.get("matcher") == "Write":
            keep_hooks = []
            for h in entry.get("hooks", []):
                if hook_command_fragment in h.get("command", ""):
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
    return settings, removed


def _write_manifest(manifest):
    """Write the deployment manifest."""
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def _read_manifest():
    """Read the deployment manifest."""
    if not MANIFEST_PATH.exists():
        return None
    with open(MANIFEST_PATH) as f:
        return json.load(f)


@click.group("plugin")
def plugin():
    """Deploy or uninstall the memory-schema plugin at user level (~/.claude/)."""
    pass


@plugin.command("deploy")
@click.option("--force", is_flag=True, help="Overwrite existing files without prompting.")
@click.pass_obj
def deploy(config, force):
    """Deploy plugin to ~/.claude/ (skills, rules, hook, memory dir).

    Creates a manifest at ~/.claude/memory-schema-manifest.json for clean uninstall.

    Example:
        memoryschema plugin deploy
        memoryschema plugin deploy --force
    """
    plugin_dir = _find_plugin_dir()
    if plugin_dir is None:
        click.echo("Error: .claude-plugin/ directory not found.", err=True)
        raise SystemExit(1)

    manifest = {
        "package": "memory-schema",
        "version": __version__,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "source": str(plugin_dir),
        "files_created": [],
        "files_overwritten": [],
        "directories_created": [],
        "hook_registered": None,
        "hook_was_existing": False,
        "settings_backup": None,
    }

    created = []
    overwritten = []
    dirs_created = []

    # 1. Deploy skills
    for src_rel, dst_rel in SKILL_FILES:
        src = plugin_dir / src_rel
        dst = CLAUDE_DIR / dst_rel
        if not src.exists():
            click.echo(f"  Warning: source not found: {src}", err=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not (dst.parent in [CLAUDE_DIR / d for d in dirs_created]):
            parent_rel = str(dst.parent.relative_to(CLAUDE_DIR))
            if not (CLAUDE_DIR / parent_rel).exists() or parent_rel not in dirs_created:
                dirs_created.append(parent_rel)
        if dst.exists() and not force:
            click.echo(f"  Exists (skip): {dst}")
            continue
        existed = dst.exists()
        shutil.copy2(src, dst)
        if existed:
            overwritten.append(str(dst))
            click.echo(f"  Overwrite: {dst}")
        else:
            created.append(str(dst))
            click.echo(f"  Created:   {dst}")

    # 2. Deploy rules
    for src_rel, dst_rel in RULE_FILES:
        src = plugin_dir / src_rel
        dst = CLAUDE_DIR / dst_rel
        if not src.exists():
            click.echo(f"  Warning: source not found: {src}", err=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        parent_rel = str(dst.parent.relative_to(CLAUDE_DIR))
        if parent_rel not in dirs_created:
            dirs_created.append(parent_rel)
        if dst.exists() and not force:
            click.echo(f"  Exists (skip): {dst}")
            continue
        existed = dst.exists()
        shutil.copy2(src, dst)
        if existed:
            overwritten.append(str(dst))
            click.echo(f"  Overwrite: {dst}")
        else:
            created.append(str(dst))
            click.echo(f"  Created:   {dst}")

    # 3. Create user-level memory directory
    memory_dir = CLAUDE_DIR / "memory"
    if not memory_dir.exists():
        memory_dir.mkdir(parents=True, exist_ok=True)
        dirs_created.append("memory")
        click.echo(f"  Created:   {memory_dir}/")

    # 4. Register hook in settings.json
    hook_script = _find_hook_script()
    if hook_script:
        hook_command = f"bash {hook_script}"
        settings = _read_settings()
        registered, existing_cmd = _hook_already_registered(settings)
        if registered:
            click.echo(f"  Hook:      already registered ({existing_cmd})")
            manifest["hook_registered"] = existing_cmd
            manifest["hook_was_existing"] = True
        else:
            settings = _add_hook(settings, hook_command)
            _write_settings(settings)
            manifest["hook_registered"] = hook_command
            manifest["hook_was_existing"] = False
            manifest["settings_backup"] = str(CLAUDE_DIR / "settings.json.memory-schema-backup")
            click.echo(f"  Hook:      registered ({hook_command})")
    else:
        click.echo("  Hook:      script not found — register manually with: memoryschema hook install", err=True)

    # 5. Write manifest
    manifest["files_created"] = created
    manifest["files_overwritten"] = overwritten
    manifest["directories_created"] = dirs_created
    _write_manifest(manifest)
    click.echo(f"\nManifest:    {MANIFEST_PATH}")
    click.echo(f"Deployed:    {len(created)} created, {len(overwritten)} overwritten")
    click.echo(f"\nUninstall:   memoryschema plugin uninstall")


@plugin.command("uninstall")
@click.option("--confirm", is_flag=True, help="Required to proceed with uninstall.")
@click.option("--keep-data", is_flag=True, help="Keep ~/.claude/memory/ data files.")
@click.pass_obj
def uninstall(config, confirm, keep_data):
    """Uninstall the memory-schema plugin from ~/.claude/.

    Reads the deployment manifest to remove exactly what was deployed.
    Requires --confirm to proceed.

    Example:
        memoryschema plugin uninstall --confirm
        memoryschema plugin uninstall --confirm --keep-data
    """
    manifest = _read_manifest()
    if manifest is None:
        click.echo("No deployment manifest found at ~/.claude/memory-schema-manifest.json")
        click.echo("Nothing to uninstall.")
        return

    click.echo(f"Deployment found: v{manifest.get('version', '?')} from {manifest.get('deployed_at', '?')}")
    click.echo(f"Files to remove: {len(manifest.get('files_created', []))}")

    if not confirm:
        click.echo("\nDry run — pass --confirm to proceed.")
        click.echo("\nWould remove:")
        for f in manifest.get("files_created", []):
            click.echo(f"  rm {f}")
        for f in manifest.get("files_overwritten", []):
            click.echo(f"  rm {f} (was overwritten)")
        if not manifest.get("hook_was_existing") and manifest.get("hook_registered"):
            click.echo(f"  unhook: {manifest['hook_registered']}")
        if not keep_data:
            memory_dir = CLAUDE_DIR / "memory"
            if memory_dir.exists():
                click.echo(f"  rm -r {memory_dir}/ (use --keep-data to preserve)")
        return

    removed = []
    errors = []

    # 1. Remove created files
    for f in manifest.get("files_created", []):
        path = Path(f)
        if path.exists():
            try:
                path.unlink()
                removed.append(f)
                click.echo(f"  Removed: {f}")
            except Exception as e:
                errors.append(f"  Error removing {f}: {e}")
        else:
            click.echo(f"  Already gone: {f}")

    # 2. Remove overwritten files (they were replaced, so just delete)
    for f in manifest.get("files_overwritten", []):
        path = Path(f)
        if path.exists():
            try:
                path.unlink()
                removed.append(f)
                click.echo(f"  Removed: {f}")
            except Exception as e:
                errors.append(f"  Error removing {f}: {e}")

    # 3. Remove empty directories (reverse order for depth-first)
    for d in reversed(manifest.get("directories_created", [])):
        dir_path = CLAUDE_DIR / d
        if d == "memory" and keep_data:
            click.echo(f"  Kept:    {dir_path}/ (--keep-data)")
            continue
        if dir_path.exists() and dir_path.is_dir():
            try:
                # Only remove if empty (or if it's a skill dir we created)
                contents = list(dir_path.iterdir())
                if not contents:
                    dir_path.rmdir()
                    click.echo(f"  Removed: {dir_path}/")
                else:
                    click.echo(f"  Kept:    {dir_path}/ (not empty)")
            except Exception as e:
                errors.append(f"  Error removing {dir_path}: {e}")

    # 4. Remove hook from settings.json (only if we added it)
    if not manifest.get("hook_was_existing") and manifest.get("hook_registered"):
        settings = _read_settings()
        settings, removed_hooks = _remove_hook(settings)
        if removed_hooks:
            _write_settings(settings)
            for h in removed_hooks:
                click.echo(f"  Unhooked: {h}")
        else:
            click.echo("  Hook:     already removed")

    # 5. Remove memory data (unless --keep-data)
    if not keep_data:
        memory_dir = CLAUDE_DIR / "memory"
        if memory_dir.exists():
            try:
                shutil.rmtree(memory_dir)
                click.echo(f"  Removed: {memory_dir}/")
            except Exception as e:
                errors.append(f"  Error removing {memory_dir}: {e}")

    # 6. Remove manifest
    try:
        MANIFEST_PATH.unlink()
        click.echo(f"  Removed: {MANIFEST_PATH}")
    except Exception as e:
        errors.append(f"  Error removing manifest: {e}")

    # Report
    if errors:
        click.echo(f"\nErrors:")
        for e in errors:
            click.echo(e)

    click.echo(f"\nUninstalled: {len(removed)} files removed")
    if keep_data:
        click.echo("Data preserved at ~/.claude/memory/")


@plugin.command("status")
@click.pass_obj
def plugin_status(config):
    """Show current deployment status."""
    manifest = _read_manifest()
    if manifest is None:
        click.echo("Not deployed (no manifest found)")
        return

    click.echo(f"Version:     {manifest.get('version', '?')}")
    click.echo(f"Deployed:    {manifest.get('deployed_at', '?')}")
    click.echo(f"Source:      {manifest.get('source', '?')}")

    # Check file health
    missing = []
    present = []
    for f in manifest.get("files_created", []) + manifest.get("files_overwritten", []):
        if Path(f).exists():
            present.append(f)
        else:
            missing.append(f)

    click.echo(f"Files:       {len(present)} present, {len(missing)} missing")
    if missing:
        for f in missing:
            click.echo(f"  Missing: {f}")

    # Check hook
    if manifest.get("hook_registered"):
        settings = _read_settings()
        registered, _ = _hook_already_registered(settings)
        click.echo(f"Hook:        {'registered' if registered else 'NOT registered'}")
    else:
        click.echo("Hook:        not managed by deploy")

    # Check memory dir
    memory_dir = CLAUDE_DIR / "memory"
    if memory_dir.exists():
        store = memory_dir / "store.jsonl"
        if store.exists():
            lines = sum(1 for _ in open(store) if _.strip())
            click.echo(f"User store:  {lines} entries")
        else:
            click.echo("User store:  empty (no store.jsonl yet)")
    else:
        click.echo("User store:  directory missing")
