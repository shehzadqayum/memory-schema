"""The deployment ledger CLI (`deploy register` / `deploy status`) — machine-stamped, reconciled vs branches.

Hermetic: a throwaway git repo in tmp_path; no network, no live backend (preflight skipped)."""
import json
import subprocess

from click.testing import CliRunner

from memoryschema.cli.main import cli


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _repo(tmp_path):
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@t"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    (tmp_path / "f").write_text("x", encoding="utf-8")
    _git(["add", "f"], tmp_path)
    _git(["commit", "-qm", "init"], tmp_path)


def test_register_writes_machine_stamped_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORYSCHEMA_SKIP_PREFLIGHT", "1")
    _repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(cli, ["deploy", "register", "--project", "proj-a",
                                   "--repo-url", "https://x/a.git", "--prefix", "packages/memory-schema"])
    assert res.exit_code == 0, res.output
    toml = (tmp_path / "deployments" / "proj-a.toml").read_text(encoding="utf-8")
    assert 'project = "proj-a"' in toml
    assert 'subtree_prefix = "packages/memory-schema"' in toml
    assert "schema_version = 5" in toml                     # stamped from CURRENT_ENTITY_FORMAT
    assert 'branch = "deployments/proj-a"' in toml
    assert "module_commit = " in toml and "registered_at = " in toml


def test_status_reconciles_ledger_against_branches(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORYSCHEMA_SKIP_PREFLIGHT", "1")
    _repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    r = CliRunner()
    # proj-a: registered but NOT pushed (no branch)
    r.invoke(cli, ["deploy", "register", "--project", "proj-a",
                   "--repo-url", "https://x/a.git", "--prefix", "pkg"])
    # proj-b: a branch with NO ledger entry
    _git(["branch", "deployments/proj-b"], tmp_path)
    res = r.invoke(cli, ["deploy", "status", "--json"])
    assert res.exit_code == 0, res.output
    by = {x["project"]: x for x in json.loads(res.output)}
    assert by["proj-a"]["registered"] and not by["proj-a"]["branch_exists"]   # registered-not-pushed
    assert by["proj-b"]["branch_exists"] and not by["proj-b"]["registered"]   # branch-only (unregistered)
    # human output surfaces both mismatch states
    txt = r.invoke(cli, ["deploy", "status"]).output
    assert "NOT-PUSHED" in txt and "UNREGISTERED" in txt


def test_status_empty_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORYSCHEMA_SKIP_PREFLIGHT", "1")
    _repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(cli, ["deploy", "status"])
    assert res.exit_code == 0
    assert "No deployments registered" in res.output
