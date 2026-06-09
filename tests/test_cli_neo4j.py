"""Tests for CLI neo4j commands (mocked Docker + Neo4j)."""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestNeo4jStatus:
    def test_status_json_docker_available(self, runner, tmp_path):
        ps_result = MagicMock(stdout="Up 2 hours", returncode=0)
        with patch("subprocess.run", side_effect=[MagicMock(), ps_result]):
            with patch("memoryschema.neo4j_store.Neo4jMemoryStore", side_effect=Exception("no")):
                result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "container" in data
        assert data["docker_available"] is True
        assert data["container_status"] == "Up 2 hours"
        assert data["connected"] is False

    def test_status_json_docker_unavailable(self, runner, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["docker_available"] is False
        assert data["container_status"] == "n/a"

    def test_status_text_container_not_created(self, runner, tmp_path):
        ps_result = MagicMock(stdout="", returncode=0)
        with patch("subprocess.run", side_effect=[MagicMock(), ps_result]):
            result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "status"])
        assert result.exit_code == 0
        assert "Docker:    installed" in result.output
        assert "not created" in result.output

    def test_status_text_docker_not_found(self, runner, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "status"])
        assert result.exit_code == 0
        assert "Docker:    not found" in result.output


class TestNeo4jSchema:
    def test_schema_success(self, runner, tmp_path):
        mock_indexes = [{"name": "test_idx", "type": "VECTOR"}]
        with patch("memoryschema.schema.setup_schema", return_value=mock_indexes):
            result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "schema"])
        assert result.exit_code == 0
        assert "verified" in result.output.lower()

    def test_schema_failure(self, runner, tmp_path):
        with patch("memoryschema.schema.setup_schema", side_effect=Exception("connection refused")):
            result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "schema"])
        assert result.exit_code != 0


class TestNeo4jReset:
    def test_requires_confirm(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "reset"])
        assert result.exit_code != 0
        assert "confirm" in result.output.lower()

    def test_with_confirm(self, runner, tmp_path):
        with patch("neo4j.GraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.run.return_value = MagicMock(single=MagicMock(return_value={"n": 5}))
            mock_gd.driver.return_value = mock_driver
            with patch("memoryschema.schema.setup_schema"):
                result = runner.invoke(cli, ["--root", str(tmp_path), "neo4j", "reset", "--confirm"])
        assert result.exit_code == 0


class TestNeo4jHelp:
    def test_group_help(self, runner):
        result = runner.invoke(cli, ["neo4j", "--help"])
        assert result.exit_code == 0
        assert "deploy" in result.output
        assert "status" in result.output
        assert "reset" in result.output
