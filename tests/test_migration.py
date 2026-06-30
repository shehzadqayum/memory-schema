"""Tests for migration module (mocked Neo4j driver)."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from memoryschema.migration import load_jsonl, entry_to_node_props, migrate
from memoryschema.config import MemoryConfig


@pytest.fixture
def jsonl_file(tmp_path):
    """Create a temp JSONL file with test entries."""
    entries = [
        {"name": "entry-1", "schema": 2, "description": "First", "importance": 5, "observations": ["A", "B"],
         "embedding": [0.1] * 10, "relations": [{"target": "entry-2", "type": "USES"}],
         "associations": [{"name": "entry-2", "score": 0.9}]},
        {"name": "entry-2", "schema": 2, "description": "Second", "importance": 7, "observations": ["C"],
         "embedding": [0.2] * 10},
        {"name": "entry-3", "schema": 2, "description": "No embedding", "importance": 3},
    ]
    path = tmp_path / "test-store.jsonl"
    with open(path, 'w') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')
    return str(path), entries


class TestLoadJsonl:
    def test_loads_entries(self, jsonl_file):
        path, expected = jsonl_file
        result = load_jsonl(path)
        assert len(result) == 3
        assert result[0]["name"] == "entry-1"

    def test_skips_malformed(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text('{"name":"good"}\nnot json\n{"name":"also-good"}\n')
        result = load_jsonl(str(path))
        assert len(result) == 2

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        result = load_jsonl(str(path))
        assert result == []


class TestEntryToNodeProps:
    def test_conversion(self):
        entry = {
            "name": "test", "schema": 2, "type": "semantic", "description": "Hello",
            "importance": 7, "observations": ["A", "B"], "created_at": "2026-01-01",
            "project": "my-project",
        }
        props = entry_to_node_props(entry)
        assert props["name"] == "test"
        assert props["description"] == "Hello"
        assert props["observations"] == ["A", "B"]
        assert props["observations_text"] == "A B"
        assert props["access_count"] == 0

    def test_empty_observations(self):
        entry = {"name": "test"}
        props = entry_to_node_props(entry)
        assert props["observations"] == []
        assert props["observations_text"] == ""


class TestMigrate:
    def test_dry_run(self, jsonl_file):
        path, entries = jsonl_file
        config = MemoryConfig(store_path=path)
        result = migrate(config=config, dry_run=True)
        assert result["dry_run"] is True
        assert result["entries"] == 3
        assert result["embedded"] == 2
        assert result["with_rels"] == 1

    def test_migrate_with_mock_driver(self, jsonl_file):
        path, entries = jsonl_file
        config = MemoryConfig(store_path=path)
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.run.return_value = MagicMock(single=MagicMock(return_value={"n": 3}))

        with patch("memoryschema.migration.connect") as mock_connect:
            mock_connect.return_value = mock_driver
            result = migrate(config=config, skip_assoc=True)
        assert result["nodes_created"] == 3
        assert "duration_s" in result

    def test_verify(self, jsonl_file):
        path, entries = jsonl_file
        from memoryschema.migration import verify
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.run.return_value = MagicMock(single=MagicMock(return_value={"n": 3}))
        result = verify(mock_driver, entries)
        assert result["jsonl_count"] == 3
        assert result["neo4j_count"] == 3
        assert result["match"] is True


class TestMigrateNodesIdempotent:
    """P1 regression: migrate_nodes must MERGE (not CREATE) on the unique name so re-running the
    import against existing nodes is idempotent (no ConstraintError on memory_name_unique).
    Mirrors the P0 schema-idempotency test. (helios local patch — re-apply on re-vendor.)"""

    def _capturing_driver(self, statements):
        drv = MagicMock()
        sess = MagicMock()
        drv.session.return_value.__enter__ = MagicMock(return_value=sess)
        drv.session.return_value.__exit__ = MagicMock(return_value=False)
        sess.run.side_effect = lambda q, **kw: statements.append(q) or MagicMock()
        return drv

    def test_uses_merge_not_create(self):
        from memoryschema.migration import migrate_nodes
        stmts = []
        entries = [{"name": "a", "schema": 4, "description": "A", "embedding": [0.1] * 4},
                   {"name": "b", "schema": 4, "description": "B"}]
        migrate_nodes(self._capturing_driver(stmts), entries)
        joined = "\n".join(stmts).upper()
        assert "MERGE (M:MEMORY {NAME:" in joined          # idempotent upsert
        assert "CREATE (M:MEMORY" not in joined            # the old non-idempotent form is gone
        assert "CREATE (N:MEMORY" not in joined

    def test_idempotent_against_already_exists(self):
        """A FakeSession that raises (like Neo4j's memory_name_unique) for an UNGUARDED CREATE of a
        node run twice. With MERGE, running migrate_nodes twice must not raise."""
        from memoryschema.migration import migrate_nodes

        class ConstraintError(Exception):
            pass

        seen = set()

        class Sess:
            def run(self, q, **kw):
                up = q.upper()
                if "CREATE (M:MEMORY" in up or "CREATE (N:MEMORY" in up:
                    key = q.strip()
                    if key in seen:
                        raise ConstraintError("memory_name_unique violated")
                    seen.add(key)
                return MagicMock()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        drv = MagicMock()
        drv.session.return_value = Sess()
        entries = [{"name": "a", "schema": 4, "description": "A", "embedding": [0.1] * 4}]
        migrate_nodes(drv, entries)
        migrate_nodes(drv, entries)   # the regression would raise here on a bare CREATE
