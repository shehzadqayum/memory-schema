"""P4: get_store() must not silently swallow a Neo4j failure.

Uses a bogus bolt URI so the Neo4j probe fails fast and deterministically (no live backend).
require_neo4j=True -> raises (write-class callers); default -> degrades to the JSONL store.
(hermetic test.)
"""
import pytest
from click.testing import CliRunner

from memoryschema.cli.index_cmd import index
from memoryschema.config import MemoryConfig
from memoryschema.store import get_store

_DOWN = dict(neo4j_uri="bolt://127.0.0.1:59999", neo4j_password="x")


def test_raises_when_required(tmp_path):
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = MemoryConfig(project_root=str(tmp_path), **_DOWN)
    with pytest.raises(ConnectionError):
        get_store(config=cfg, require_neo4j=True)


def test_degrades_to_jsonl_when_not_required(tmp_path):
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = MemoryConfig(project_root=str(tmp_path), **_DOWN)
    store = get_store(config=cfg, require_neo4j=False)
    assert type(store).__name__ == "MemoryStore"     # fell back to JSONL, did not raise


def test_index_command_fails_loud_when_neo4j_required_and_down(tmp_path):
    """The explicit `index` materialize command hard-fails (non-zero, clean message) when
    Neo4j is required (default) but unreachable -- it must not silently write JSONL-only."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = MemoryConfig(project_root=str(tmp_path), require_neo4j=True, **_DOWN)
    result = CliRunner().invoke(index, [], obj=cfg)
    assert result.exit_code != 0                      # loud, not silent
    assert "Neo4j" in result.output                   # actionable message, not a bare trace


def test_index_command_degrades_when_neo4j_not_required(tmp_path):
    """With require_neo4j=false the same command is allowed to degrade to JSONL-only (exit 0)."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = MemoryConfig(project_root=str(tmp_path), require_neo4j=False, **_DOWN)
    result = CliRunner().invoke(index, [], obj=cfg)
    assert result.exit_code == 0                       # JSONL-only degrade permitted


def test_degraded_banner_printed_to_stderr(tmp_path, capsys, monkeypatch):
    """The JSONL fallback must be LOUD: a DEGRADED banner reaches stderr when degrading."""
    monkeypatch.delenv("MEMORYSCHEMA_SKIP_PREFLIGHT", raising=False)   # un-quiet it for this test
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = MemoryConfig(project_root=str(tmp_path), **_DOWN)
    get_store(config=cfg, require_neo4j=False)
    err = capsys.readouterr().err
    assert "DEGRADED" in err and "Neo4j unreachable" in err


def test_degraded_banner_suppressed_under_skip_preflight(tmp_path, capsys, monkeypatch):
    """Self-checking contexts (tests/hooks) set SKIP_PREFLIGHT — the banner is then suppressed."""
    monkeypatch.setenv("MEMORYSCHEMA_SKIP_PREFLIGHT", "1")
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = MemoryConfig(project_root=str(tmp_path), **_DOWN)
    get_store(config=cfg, require_neo4j=False)
    err = capsys.readouterr().err
    assert "DEGRADED" not in err
