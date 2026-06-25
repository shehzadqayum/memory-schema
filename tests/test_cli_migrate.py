"""Tests for CLI migrate and sync commands."""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestMigrateJsonlToNeo4j:
    def test_dry_run(self, runner, tmp_path):
        store_path = tmp_path / "memory" / "store.jsonl"
        store_path.parent.mkdir(parents=True)
        store_path.write_text('{"name":"a","schema":2,"description":"A"}\n')
        mock_result = {"entries": 1, "embedded": 0, "with_assoc": 0, "with_rels": 0, "dry_run": True}
        with patch("memoryschema.migration.migrate", return_value=mock_result):
            result = runner.invoke(cli, ["--root", str(tmp_path), "migrate", "jsonl-to-neo4j", "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()

    def test_help(self, runner):
        result = runner.invoke(cli, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "jsonl-to-neo4j" in result.output


class TestSync:
    def test_sync(self, runner, tmp_path):
        store_path = tmp_path / "memory" / "store.jsonl"
        store_path.parent.mkdir(parents=True)
        store_path.write_text("")
        with patch("memoryschema.neo4j_store.Neo4jMemoryStore", side_effect=Exception("no neo4j")):
            result = runner.invoke(cli, ["--root", str(tmp_path), "sync"])
        assert result.exit_code == 0
        assert "JSONL" in result.output
