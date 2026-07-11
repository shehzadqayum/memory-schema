"""CLI: the deployment ledger — a machine-stamped registry of which projects vendor this module.

Architecture (see DEPLOYMENT.md): the module repo is the SINGLE SOURCE OF TRUTH. Consumers vendor it via
`git subtree`; each consumer's state is pushed to a `deployments/<project>` branch. This ledger — one
`deployments/<project>.toml` per project on the module's `main`, plus the `deployments/*` branch list —
records the pointer + last-sync facts. Deterministic tooling writes it (a hand-maintained registry rots — the
same lesson that retired HANDOVER.md).
"""
import json
import os
import subprocess
from datetime import date

import click


def _git(args, cwd=None):
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _module_root():
    """The module repo root (where the ledger lives)."""
    return _git(["rev-parse", "--show-toplevel"])


def _ledger_dir(root):
    return os.path.join(root, "deployments")


def _esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _read_ledger_toml(path):
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f).get("deployment", {})
    except Exception:
        return {}


def _deployment_branches(root):
    """The set of project names that have a `deployments/<name>` branch (local or remote)."""
    out = _git(["branch", "-a", "--list", "*deployments/*"], cwd=root) or ""
    names = set()
    for ln in out.splitlines():
        ln = ln.strip().lstrip("* ").strip()
        if "deployments/" in ln:
            names.add(ln.split("deployments/", 1)[1].strip())
    return names


@click.group("deploy")
def deploy():
    """The deployment ledger — records which projects vendor this module (see DEPLOYMENT.md)."""


@deploy.command("register")
@click.option("--project", required=True, help="The consuming project's name.")
@click.option("--repo-url", required=True, help="The consuming project's git remote URL.")
@click.option("--prefix", required=True,
              help="The subtree prefix inside the consumer repo (e.g. packages/memory-schema).")
@click.option("--scopes", default="working", help="Deployed rule scopes (comma-separated).")
@click.option("--consumer-commit", default=None, help="The consumer repo's HEAD at last sync (optional).")
@click.option("--note", default="", help="Free-text note.")
def register(project, repo_url, prefix, scopes, consumer_commit, note):
    """Upsert this project's ledger entry (`deployments/<project>.toml` on the module repo).

    Run from inside the MODULE repo (the single source of truth). Deterministic: it stamps the module's
    current HEAD, the subtree pointer, the schema version, and the date — so `deploy status` is always true.

    Example:
        memoryschema deploy register --project helios \\
            --repo-url https://github.com/me/helios.git --prefix packages/memory-schema
    """
    root = _module_root()
    if not root:
        click.echo("Error: not inside a git repo — run `deploy register` in the module repo.", err=True)
        raise SystemExit(1)
    from memoryschema.entity_schema import CURRENT_ENTITY_FORMAT
    ld = _ledger_dir(root)
    os.makedirs(ld, exist_ok=True)
    path = os.path.join(ld, f"{project}.toml")
    module_commit = _git(["rev-parse", "HEAD"], cwd=root) or "unknown"
    scope_list = ", ".join(f'"{_esc(s.strip())}"' for s in scopes.split(",") if s.strip())
    body = "\n".join([
        "# machine-written by `memoryschema deploy register` — do not hand-edit",
        "[deployment]",
        f'project = "{_esc(project)}"',
        f'repo_url = "{_esc(repo_url)}"',
        f'subtree_prefix = "{_esc(prefix)}"',
        f'scopes = [{scope_list}]',
        f'schema_version = {CURRENT_ENTITY_FORMAT}',
        f'branch = "deployments/{_esc(project)}"',
        f'module_commit = "{module_commit}"',
        f'consumer_commit = "{_esc(consumer_commit or "")}"',
        f'registered_at = "{date.today().isoformat()}"',
        f'note = "{_esc(note)}"',
        "",
    ])
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    click.echo(f"Registered: {os.path.relpath(path, root)}  (push the consumer state to branch "
               f"deployments/{project})")


@deploy.command("status")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
def status(as_json):
    """Show the ledger: registered projects reconciled against the `deployments/*` branches.

    A ledger entry with no branch = registered-but-not-pushed; a branch with no entry = unregistered. Both
    are surfaced so the ledger and the branches can never silently disagree.
    """
    root = _module_root()
    if not root:
        click.echo("Error: not inside a git repo.", err=True)
        raise SystemExit(1)
    ld = _ledger_dir(root)
    entries = {}
    if os.path.isdir(ld):
        for fn in sorted(os.listdir(ld)):
            if fn.endswith(".toml"):
                entries[fn[:-5]] = _read_ledger_toml(os.path.join(ld, fn))
    branches = _deployment_branches(root)
    rows = []
    for name in sorted(set(entries) | branches):
        e = entries.get(name, {})
        rows.append({
            "project": name,
            "registered": name in entries,
            "branch_exists": name in branches,
            "repo_url": e.get("repo_url"),
            "subtree_prefix": e.get("subtree_prefix"),
            "module_commit": e.get("module_commit"),
            "registered_at": e.get("registered_at"),
        })
    if as_json:
        click.echo(json.dumps(rows, indent=2))
        return
    if not rows:
        click.echo("No deployments registered. Register one with `memoryschema deploy register`.")
        return
    click.echo(f"Deployment ledger ({len(rows)} project(s)):")
    for r in rows:
        flags = []
        if not r["registered"]:
            flags.append("UNREGISTERED (branch only)")
        if not r["branch_exists"]:
            flags.append("NOT-PUSHED (no deployments/ branch)")
        click.echo(f"  {r['project']:<20} {' '.join(flags) or 'ok'}")
        if r["registered"]:
            click.echo(f"      prefix={r['subtree_prefix']}  module@{(r['module_commit'] or '')[:9]}"
                       f"  since {r['registered_at']}")
