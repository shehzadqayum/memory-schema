"""CLI-level (CliRunner) tests for the always-on reconcile/preflight commands. (helios local patch.)"""
import json

from click.testing import CliRunner

from memoryschema.cli.migrate_cmd import reconcile as reconcile_cmd
from memoryschema.cli.preflight_cmd import preflight as preflight_cmd
from memoryschema.config import MemoryConfig

_ENTITY = ('<memory:entity schema="4" name="x">'
           '<memory:description>X</memory:description></memory:entity>')


def test_reconcile_dry_run_cli(tmp_path, dead_neo4j):
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "x.md").write_text(_ENTITY, encoding="utf-8")
    r = CliRunner().invoke(reconcile_cmd, ["--dry-run"], obj=dead_neo4j(project_root=str(tmp_path)))
    assert r.exit_code == 0
    assert "dry run" in r.output.lower()
    assert "unreachable" in r.output.lower()      # Neo4j down -> reported as unreachable, not "0"


def test_reconcile_aborts_on_empty_md_cli(tmp_path, dead_neo4j):
    """The CLI surfaces the safety guard as a non-zero ABORTED exit and preserves the store."""
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "store.jsonl").write_text('{"name":"a","schema":4}\n{"name":"b","schema":4}\n', encoding="utf-8")
    r = CliRunner().invoke(reconcile_cmd, [], obj=dead_neo4j(project_root=str(tmp_path)))
    assert r.exit_code != 0
    assert "ABORTED" in r.output
    assert (mem / "store.jsonl").read_text(encoding="utf-8").count("\n") == 2   # preserved


def test_import_hard_fails_when_neo4j_required_and_down(tmp_path, dead_neo4j):
    """`import` is an explicit materialize command: hard-fails loud when Neo4j is required + down."""
    from memoryschema.cli.lifecycle_cmd import import_cmd
    src = tmp_path / "in.jsonl"
    src.write_text('{"name":"a","schema":4}\n', encoding="utf-8")
    cfg = dead_neo4j(project_root=str(tmp_path), require_neo4j=True)
    r = CliRunner().invoke(import_cmd, [str(src), "--format", "jsonl"], obj=cfg)
    assert r.exit_code != 0
    assert "Neo4j" in r.output


def test_write_hard_fails_when_neo4j_required_and_down(tmp_path, dead_neo4j):
    """`write` likewise hard-fails loud rather than writing JSONL-only that drifts."""
    from memoryschema.cli.memory_cmd import write as write_cmd
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    mdf = tmp_path / "memory" / "m.md"
    mdf.write_text('<memory:entity schema="4" name="m">'
                   '<memory:description>M</memory:description></memory:entity>', encoding="utf-8")
    cfg = dead_neo4j(project_root=str(tmp_path), require_neo4j=True)
    r = CliRunner().invoke(write_cmd, [str(mdf)], obj=cfg)
    assert r.exit_code != 0
    assert "Neo4j" in r.output


def test_recall_stats_cli(tmp_path, dead_neo4j, monkeypatch):
    """recall-stats reads the telemetry log and reports usage."""
    from memoryschema.cli.memory_cmd import recall_stats
    from memoryschema import recall_log
    monkeypatch.delenv("MEMORYSCHEMA_RECALL_LOG", raising=False)   # re-enable for this test
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = dead_neo4j(project_root=str(tmp_path))
    recall_log.log_recall(cfg, "q", [{"name": "alpha", "score": 0.8, "channel": "seed"}],
                          backend="Neo4jMemoryStore", now="2026-06-30T10:00:00+00:00")
    r = CliRunner().invoke(recall_stats, [], obj=cfg)
    assert r.exit_code == 0
    assert "Recall events:" in r.output


def test_preflight_json_failure_cli(monkeypatch):
    """preflight --json exits non-zero and emits valid JSON with ok=False when a hard dep is down."""
    import memoryschema.preflight as pf
    monkeypatch.setattr(pf, "_docker_engine_up", lambda: False)
    monkeypatch.setattr(pf, "_voyage_ok", lambda c: (True, "ok"))
    cfg = MemoryConfig(project_root=".")
    r = CliRunner().invoke(preflight_cmd, ["--json", "--no-auto-start", "--require", "neo4j"], obj=cfg)
    assert r.exit_code != 0
    data = json.loads(r.output)
    assert data["ok"] is False
