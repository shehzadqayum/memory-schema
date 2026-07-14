"""v0.1.2 regressions: lifecycle flips must reach BOTH stores + the .md (defect 2, 2026-07-14).

archive/unarchive/reactivate ran on the ACTIVE backend only (Neo4j when up) — the JSONL mirror kept
the old status until the next reconcile, sync's name-set diff couldn't see it, and dream (which
reads JSONL statuses) offered an already-archived chain as a distill candidate. The commands now
replay the flip onto the JSONL mirror; reactivate additionally persists to the .md (file-first —
without it the next reconcile silently REVERTED a reactivation).
"""
import json

from click.testing import CliRunner

import memoryschema.cli.memory_cmd as memory_cmd
from memoryschema.cli.main import cli
from memoryschema.neo4j_store import Neo4jMemoryStore

ENV = {"MEMORYSCHEMA_SKIP_PREFLIGHT": "1", "NEO4J_URI": "bolt://127.0.0.1:59999"}


class _FakeNeo4j(Neo4jMemoryStore):
    """isinstance-compatible fake: records lifecycle calls, never connects."""

    def __init__(self):                                      # deliberately no super().__init__
        self.calls = []

    def archive(self, name):
        self.calls.append(("archive", name))
        return True

    def unarchive(self, name):
        self.calls.append(("unarchive", name))
        return True

    def reactivate(self, name):
        self.calls.append(("reactivate", name))
        return True


def _project(tmp_path, md_status_line="", jsonl_status=None):
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "q.md").write_text(
        f"---\nschema: 5\n{md_status_line}---\n\nQ entity.\n", encoding="utf-8")
    row = {"name": "q", "schema": 5, "description": "Q entity."}
    if jsonl_status:
        row["status"] = jsonl_status
    (tmp_path / "memory" / "store.jsonl").write_text(
        json.dumps(row) + "\n", encoding="utf-8")


def _jsonl_status(tmp_path):
    row = json.loads(
        (tmp_path / "memory" / "store.jsonl").read_text(encoding="utf-8").splitlines()[0])
    return row.get("status") or "active"


def test_archive_flips_neo4j_jsonl_and_md(tmp_path, monkeypatch):
    _project(tmp_path)
    fake = _FakeNeo4j()
    monkeypatch.setattr(memory_cmd, "_get_store", lambda config: fake)
    r = CliRunner().invoke(cli, ["--root", str(tmp_path), "archive", "q"], env=ENV)
    assert r.exit_code == 0, r.output
    assert ("archive", "q") in fake.calls                    # the active backend
    assert _jsonl_status(tmp_path) == "archived"             # the JSONL mirror (the defect)
    assert "status: archived" in (tmp_path / "memory" / "q.md").read_text(encoding="utf-8")


def test_reactivate_persists_to_md_and_mirror(tmp_path, monkeypatch):
    _project(tmp_path, md_status_line="status: superseded\n", jsonl_status="superseded")
    fake = _FakeNeo4j()
    monkeypatch.setattr(memory_cmd, "_get_store", lambda config: fake)
    r = CliRunner().invoke(cli, ["--root", str(tmp_path), "reactivate", "q"], env=ENV)
    assert r.exit_code == 0, r.output
    assert ("reactivate", "q") in fake.calls
    assert _jsonl_status(tmp_path) == "active"               # mirror replayed
    md = (tmp_path / "memory" / "q.md").read_text(encoding="utf-8")
    assert "status: superseded" not in md                    # file-first: reconcile must not revert
