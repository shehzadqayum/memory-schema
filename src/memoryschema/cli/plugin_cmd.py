"""CLI commands for deploying/uninstalling the memory-schema plugin at user level (~/.claude/)."""

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from memoryschema._version import __version__
from memoryschema.cli._hooks_util import (
    find_hook_script_path,
    find_stop_hook_script_path,
    hook_already_registered,
    read_settings,
    register_hooks,
    unregister_hooks,
    write_settings,
)


CLAUDE_DIR = Path.home() / ".claude"
MANIFEST_PATH = CLAUDE_DIR / "memory-schema-manifest.json"

# The CANONICAL operational artefacts (source relative to the plugin dir → target relative to a `.claude/`).
# The package's `src/memoryschema/claude_plugin/` is the SINGLE SOURCE OF TRUTH; BOTH `plugin sync` and `init` deploy from it
# via `deploy_artefacts` — there is no second (template) copy of these to drift against.
_KERNEL_PAIR = ("rules/memory-working.md", "rules/memory-working.md")                    # always-loaded kernel
_SCHEMA_PAIR = ("rules-ondemand/memory-schema.md", "rules-ondemand/memory-schema.md")    # on-demand v5 schema ref
_CORPUS_PAIR = ("rules-ondemand/memory-corpus.md", "rules-ondemand/memory-corpus.md")    # on-demand corpus rule

SKILL_FILES = [
    ("skills/dream-pass/SKILL.md", "skills/dream-pass/SKILL.md"),
]
RULE_FILES = [_KERNEL_PAIR, _SCHEMA_PAIR, _CORPUS_PAIR]

# Scope-gated on-demand rules (the kernel + schema ref always deploy; these are opt-in via `init --scopes`).
_SCOPE_RULE_PAIRS = {"corpus": _CORPUS_PAIR}


def artefact_pairs_for_scopes(scopes):
    """The (src_rel, dst_rel) artefacts a deployment with these scopes carries: the dream-pass skill, the
    always-loaded kernel, the on-demand schema reference, plus any scope-specific on-demand rules. Used by
    `init` so it deploys the SAME artefacts (from the SAME source) as `plugin sync`."""
    pairs = list(SKILL_FILES) + [_KERNEL_PAIR, _SCHEMA_PAIR]
    pairs += [_SCOPE_RULE_PAIRS[s] for s in scopes if s in _SCOPE_RULE_PAIRS]
    return pairs


def deploy_artefacts(src_dir, base, pairs):
    """MD5-gated copy of `pairs` from src_dir into `base` (a `.claude/` dir). Writes only missing/changed
    files (so a re-run is a no-op on in-sync files); returns the dst paths actually written. The one
    deployment path shared by `plugin sync` and `init`."""
    written = []
    for r in compute_artefact_sync(src_dir, base, pairs=pairs):
        if r["status"] in ("missing", "drift"):
            r["dst"].parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(r["src"], r["dst"])
            written.append(str(r["dst"]))
    return written


def _find_plugin_dir():
    """Locate the deployable-artefacts dir (the plugin SSOT). Packaged UNDER the module (`claude_plugin/`,
    shipped as package-data), so it resolves from ANY install — editable OR a real wheel — not just a source
    checkout. This is what lets `plugin sync`/`init` work in a project that merely `pip install`ed the module."""
    try:
        from importlib.resources import files as pkg_files
        cand = Path(str(pkg_files("memoryschema"))) / "claude_plugin"
        if cand.is_dir():
            return cand
    except Exception:
        pass
    cand = Path(__file__).resolve().parent.parent / "claude_plugin"  # src/memoryschema/ (source-tree fallback)
    return cand if cand.is_dir() else None


def _write_manifest(manifest):
    """Write the deployment manifest."""
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def _read_manifest():
    """Read the deployment manifest."""
    if not MANIFEST_PATH.exists():
        return None
    with open(MANIFEST_PATH, encoding="utf-8") as f:
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
        click.echo("Error: src/memoryschema/claude_plugin/ directory not found.", err=True)
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

    # 4. Register hooks in settings.json
    hook_script = find_hook_script_path()
    stop_hook_script = find_stop_hook_script_path()
    if hook_script:
        hook_command = f"bash {hook_script} {sys.executable}"
        stop_hook_command = f"bash {stop_hook_script}" if stop_hook_script else None
        settings_path = CLAUDE_DIR / "settings.json"
        settings = read_settings(settings_path)
        registered, existing_cmd = hook_already_registered(settings)
        if registered:
            click.echo(f"  Hook:      already registered ({existing_cmd})")
            manifest["hook_registered"] = existing_cmd
            manifest["hook_was_existing"] = True
        else:
            register_hooks(settings, hook_command, stop_hook_command)
            write_settings(settings_path, settings, backup=True)
            manifest["hook_registered"] = hook_command
            manifest["hook_was_existing"] = False
            manifest["settings_backup"] = str(CLAUDE_DIR / "settings.json.memory-schema-backup")
            click.echo(f"  Hook:      registered ({hook_command})")
            if stop_hook_command:
                click.echo(f"  Stop hook: registered ({stop_hook_command})")
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
        settings_path = CLAUDE_DIR / "settings.json"
        settings = read_settings(settings_path)
        settings, removed_hooks = unregister_hooks(settings)
        if removed_hooks:
            write_settings(settings_path, settings, backup=True)
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
        settings_path = CLAUDE_DIR / "settings.json"
        settings = read_settings(settings_path)
        registered, _ = hook_already_registered(settings)
        click.echo(f"Hook:        {'registered' if registered else 'NOT registered'}")
    else:
        click.echo("Hook:        not managed by deploy")

    # Check memory dir
    memory_dir = CLAUDE_DIR / "memory"
    if memory_dir.exists():
        store = memory_dir / "store.jsonl"
        if store.exists():
            lines = sum(1 for _ in open(store, encoding="utf-8") if _.strip())
            click.echo(f"User store:  {lines} entries")
        else:
            click.echo("User store:  empty (no store.jsonl yet)")
    else:
        click.echo("User store:  directory missing")


# ---------------------------------------------------------------------------
# Mechanical, checksum-verified sync of the canonical memory artefacts
# ---------------------------------------------------------------------------

def _md5(path):
    """MD5 hex digest of a file (streamed)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _artefact_pairs():
    """(source_rel, target_rel) for every canonical memory artefact — the
    complete set the package is the single source of truth for."""
    return list(SKILL_FILES) + list(RULE_FILES)


def compute_artefact_sync(src_dir, base, pairs=None):
    """Compare each artefact's MD5 against its deployed copy.

    `pairs` defaults to the complete canonical set (`_artefact_pairs()`); pass a subset (e.g. from
    `artefact_pairs_for_scopes`) to scope a deployment. Returns a list of
    {file, status, src_md5, dst_md5, src, dst}. Status is one of src-missing (source of truth absent — a
    package defect), missing (not deployed), drift (deployed copy differs), in-sync (MD5 match). Read-only.
    """
    rows = []
    for src_rel, dst_rel in (pairs if pairs is not None else _artefact_pairs()):
        s = Path(src_dir) / src_rel
        d = Path(base) / dst_rel
        s_md5 = _md5(s) if s.exists() else None
        d_md5 = _md5(d) if d.exists() else None
        if s_md5 is None:
            status = "src-missing"
        elif d_md5 is None:
            status = "missing"
        elif s_md5 == d_md5:
            status = "in-sync"
        else:
            status = "drift"
        rows.append({"file": dst_rel, "status": status,
                     "src_md5": s_md5, "dst_md5": d_md5, "src": s, "dst": d})
    return rows


@plugin.command("sync")
@click.option("--check", is_flag=True,
              help="Verify only (MD5): report drift, write nothing. Exit 1 on any drift/missing.")
@click.option("--target", type=click.Path(), default=None,
              help="Target .claude directory. Default: <project_root>/.claude.")
@click.option("--global", "use_global", is_flag=True,
              help="Sync to ~/.claude instead of the project.")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.pass_obj
def sync(config, check, target, use_global, as_json):
    """Sync the deployed memory artefacts FROM the package into a project's .claude/,
    verified by MD5.

    The canonical artefacts (the dream-pass skill, the kernel, the on-demand rules) live
    in the package at src/memoryschema/claude_plugin/ — the SINGLE SOURCE OF TRUTH. This makes a
    deployment's .claude/ a verifiable derived copy:

      --check   report drift and exit non-zero (a CI / pre-commit gate); writes nothing.
      (default) copy only the files that are missing or differ; leave in-sync files alone.

    Machine/ops-specific artefacts (the SessionStart hook, ensure-deps.ps1, the tuned
    memoryschema.toml) are deployment-local by design and are NOT touched here.
    """
    src_dir = _find_plugin_dir()
    if not src_dir:
        click.echo("Error: package src/memoryschema/claude_plugin/ not found — the source of truth is missing.", err=True)
        sys.exit(1)
    if use_global:
        base = CLAUDE_DIR
    elif target:
        base = Path(target)
    else:
        base = Path(config.project_root) / ".claude"
    base = Path(base).resolve()

    rows = compute_artefact_sync(src_dir, base)
    src_missing = [r for r in rows if r["status"] == "src-missing"]
    changed = [r for r in rows if r["status"] in ("missing", "drift")]

    if not check:
        for r in changed:
            r["dst"].parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(r["src"], r["dst"])
            r["status"] = "written"

    if as_json:
        click.echo(json.dumps(
            [{k: v for k, v in r.items() if k not in ("src", "dst")} for r in rows], indent=1))
    else:
        mode = "check" if check else "deploy"
        click.echo(f"Memory artefact sync ({mode})")
        click.echo(f"  source: {src_dir}")
        click.echo(f"  target: {base}")
        marks = {"in-sync": "=", "written": "+", "missing": "!", "drift": "~", "src-missing": "x"}
        for r in rows:
            click.echo("  %s %-11s %s  (%s)" % (
                marks.get(r["status"], "?"), r["status"], r["file"], (r["src_md5"] or "--------")[:8]))

    # Exit semantics: a broken source of truth always fails; --check fails on any drift.
    if src_missing:
        click.echo("  ERROR: %d artefact(s) missing from the package source." % len(src_missing), err=True)
        sys.exit(1)
    if check and changed:
        click.echo("  DRIFT: %d file(s) differ from the package — run `memoryschema plugin sync`." % len(changed), err=True)
        sys.exit(1)
    if not check and changed:
        click.echo("  Synced %d file(s) from the package (single source of truth)." % len(changed))
