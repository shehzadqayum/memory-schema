"""Temporal validity slice: fact-keys, deterministic write-time supersession,
point-in-time recall, and file-first lifecycle persistence.

Evidence base (plan-memory-direction-2026): retrieval-time staleness handling
scores <10% across frameworks (STALE benchmark); deterministic write-side
adjudication lifts it to 68%. The mechanism here is exact-key matching in
code — no LLM judgment anywhere.
"""

import json
import os

import pytest
from click.testing import CliRunner

from memoryschema.cli.main import cli
from memoryschema.format_v5 import parse_v5_content, serialize_v5
from memoryschema.tags import parse_memory_file
from memoryschema.write_index import find_active_by_key, set_lifecycle


@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    (tmp_path / "memory").mkdir()
    monkeypatch.setenv("MEMORYSCHEMA_V5", "1")
    return tmp_path


class TestFormatTemporalFields:
    def test_roundtrip(self):
        m = {"schema": 5, "name": "fact-x", "description": "d",
             "observations": ["o"], "key": "EURUSD.bias",
             "valid_from": "2026-07-01", "superseded_at": "2026-07-05",
             "superseded_by": "fact-y", "status": "superseded"}
        out = serialize_v5(m)
        back = parse_v5_content(out, filepath="fact-x.md")
        assert back["key"] == "EURUSD.bias"
        assert back["valid_from"] == "2026-07-01"
        assert back["superseded_at"] == "2026-07-05"
        assert back["superseded_by"] == "fact-y"
        assert back["status"] == "superseded"

    def test_absent_fields_stay_absent(self):
        m = {"schema": 5, "name": "n", "description": "d", "observations": ["o"]}
        back = parse_v5_content(serialize_v5(m), filepath="n.md")
        for f in ("key", "valid_from", "superseded_at", "superseded_by"):
            assert f not in back


class TestSetLifecycle:
    def test_persists_to_frontmatter(self, project_dir):
        p = project_dir / "memory" / "e1.md"
        p.write_text(serialize_v5({"schema": 5, "name": "e1", "description": "d",
                                   "observations": ["o"]}), encoding="utf-8")
        set_lifecycle(str(p), status="superseded", superseded_at="2026-07-05",
                      superseded_by="e2")
        content = p.read_text(encoding="utf-8")
        assert "status: superseded" in content
        assert "superseded_at: 2026-07-05" in content
        assert "superseded_by: e2" in content
        m = parse_memory_file(str(p))          # survives the standard parse path
        assert m["status"] == "superseded"


class TestFindActiveByKey:
    def test_exact_key_active_only(self, project_dir):
        sp = str(project_dir / "memory" / "store.jsonl")
        rows = [
            {"name": "old-active", "key": "K.a", "status": "active"},
            {"name": "old-superseded", "key": "K.a", "status": "superseded"},
            {"name": "other-key", "key": "K.b"},
        ]
        with open(sp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        assert find_active_by_key(sp, "K.a") == "old-active"
        assert find_active_by_key(sp, "K.a", exclude="old-active") is None
        assert find_active_by_key(sp, "K.b") == "other-key"     # absent status = active
        assert find_active_by_key(sp, "K.zzz") is None
        assert find_active_by_key(sp, None) is None


class TestRememberKeySupersession:
    def test_end_to_end(self, runner, project_dir):
        r1 = runner.invoke(cli, ["--root", str(project_dir), "remember", "bias-v1",
                                 "--desc", "EURUSD bearish", "--obs", "below the level",
                                 "--key", "EURUSD.bias", "--valid-from", "2026-07-01"])
        assert r1.exit_code == 0, r1.output
        f1 = parse_memory_file(str(project_dir / "memory" / "bias-v1.md"))
        assert f1["key"] == "EURUSD.bias" and f1["valid_from"] == "2026-07-01"

        r2 = runner.invoke(cli, ["--root", str(project_dir), "remember", "bias-v2",
                                 "--desc", "EURUSD bullish now", "--obs", "reclaimed the level",
                                 "--key", "EURUSD.bias"])
        assert r2.exit_code == 0, r2.output
        assert "superseded: bias-v1" in r2.output

        old = parse_memory_file(str(project_dir / "memory" / "bias-v1.md"))
        assert old["status"] == "superseded"
        assert old["superseded_by"] == "bias-v2"
        assert old.get("superseded_at")

        new = parse_memory_file(str(project_dir / "memory" / "bias-v2.md"))
        assert {"type": "SUPERSEDES", "target": "bias-v1"} in new["relations"]

        # store reflects both states (JSONL fallback path in tests)
        entries = {json.loads(l)["name"]: json.loads(l) for l in
                   open(project_dir / "memory" / "store.jsonl", encoding="utf-8") if l.strip()}
        assert entries["bias-v1"]["status"] == "superseded"
        assert (entries["bias-v2"].get("status") or "active") == "active"

    def test_no_key_no_supersession(self, runner, project_dir):
        runner.invoke(cli, ["--root", str(project_dir), "remember", "plain-a",
                            "--desc", "d", "--obs", "o"])
        r = runner.invoke(cli, ["--root", str(project_dir), "remember", "plain-b",
                                "--desc", "d2", "--obs", "o2"])
        assert "superseded" not in r.output
        a = parse_memory_file(str(project_dir / "memory" / "plain-a.md"))
        assert (a.get("status") or "active") == "active"


class TestRecallAsOf:
    def test_point_in_time_window(self, runner, project_dir):
        runner.invoke(cli, ["--root", str(project_dir), "remember", "fact-old",
                            "--desc", "old truth about widget", "--obs", "widget was blue",
                            "--key", "widget.color", "--valid-from", "2026-06-01"])
        runner.invoke(cli, ["--root", str(project_dir), "remember", "fact-new",
                            "--desc", "new truth about widget", "--obs", "widget is red",
                            "--key", "widget.color"])
        # default recall: only the CURRENT fact surfaces
        cur = runner.invoke(cli, ["--root", str(project_dir), "recall", "widget", "--limit", "5"])
        assert "fact-new" in cur.output and "fact-old" not in cur.output
        # as-of a date inside the OLD window: the old fact surfaces (new not yet valid)
        past = runner.invoke(cli, ["--root", str(project_dir), "recall", "widget",
                                   "--limit", "5", "--as-of", "2026-06-15"])
        assert "fact-old" in past.output, past.output
        assert "fact-new" not in past.output


class TestArchivePersistsFileFirst:
    def test_archive_writes_frontmatter(self, runner, project_dir):
        """Regression for the found bug: archive was store-only, so reconcile
        (rebuilding FROM .md) silently resurrected archived entities."""
        runner.invoke(cli, ["--root", str(project_dir), "remember", "to-arch",
                            "--desc", "d", "--obs", "o"])
        r = runner.invoke(cli, ["--root", str(project_dir), "archive", "to-arch"])
        assert r.exit_code == 0, r.output
        content = (project_dir / "memory" / "to-arch.md").read_text(encoding="utf-8")
        assert "status: archived" in content
        # and unarchive restores
        runner.invoke(cli, ["--root", str(project_dir), "unarchive", "to-arch"])
        content = (project_dir / "memory" / "to-arch.md").read_text(encoding="utf-8")
        assert "status:" not in content        # active = default, omitted
