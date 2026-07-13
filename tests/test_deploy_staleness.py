"""The ledger-staleness detector: `deploy status` must flag a ledger stamp that is behind the
module's current main — the stamp and the consumer branch go stale TOGETHER after a consumer
updates, so comparing them only to each other can never catch the drift (found live: helios's
entry sat 6 commits behind after the v0.1.1 cycle with a clean-looking status)."""
import json
import os
import subprocess

from click.testing import CliRunner

from memoryschema.cli.main import cli


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True)


def test_deploy_status_flags_stale_ledger(tmp_path, monkeypatch):
    repo = tmp_path / "module"
    repo.mkdir()
    _git(["init", "-q", "-b", "main"], repo)
    _git(["config", "user.email", "t@t"], repo)
    _git(["config", "user.name", "t"], repo)
    (repo / "a.txt").write_text("one", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "one"], repo)
    old_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                             capture_output=True, text=True).stdout.strip()
    # ledger stamped at commit one...
    ld = repo / "deployments"
    ld.mkdir()
    (ld / "consumer.toml").write_text(
        "[deployment]\n"
        'project = "consumer"\nrepo_url = "https://example.invalid/x.git"\n'
        'subtree_prefix = "packages/memory-schema"\n'
        f'module_commit = "{old_sha}"\nregistered_at = "2026-07-13"\n', encoding="utf-8")
    # ...then main moves on (the consumer-update drift)
    (repo / "a.txt").write_text("two", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "two"], repo)

    monkeypatch.chdir(repo)
    r = CliRunner().invoke(cli, ["deploy", "status", "--json"],
                           env={"MEMORYSCHEMA_SKIP_PREFLIGHT": "1"})
    assert r.exit_code == 0, r.output
    rows = {x["project"]: x for x in json.loads(r.output)}
    assert rows["consumer"]["module_behind"] == 1, "the stale stamp must be measured against main"

    human = CliRunner().invoke(cli, ["deploy", "status"],
                               env={"MEMORYSCHEMA_SKIP_PREFLIGHT": "1"})
    assert "STALE ledger" in human.output
