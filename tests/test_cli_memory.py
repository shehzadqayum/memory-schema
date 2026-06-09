"""Tests for CLI memory operations — status, recall, get, list, write, delete, search."""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.count.return_value = 42
    store.get.return_value = {"name": "test", "description": "Hello", "type": "semantic",
                               "importance": 7, "observations": ["Fact"]}
    store.search.return_value = [{"name": "a", "description": "Alpha", "importance": 5}]
    store.recall.return_value = [{"name": "a", "score": 0.8, "channel": "seed",
                                   "description": "Alpha", "type": "semantic"}]
    store.delete.return_value = True
    with patch("memoryschema.cli.memory_cmd._get_store", return_value=store):
        yield store


class TestStatus:
    def test_output(self, runner, mock_store):
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "42" in result.output

    def test_json(self, runner, mock_store):
        result = runner.invoke(cli, ["status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["nodes"] == 42


class TestRecall:
    def test_basic(self, runner, mock_store):
        result = runner.invoke(cli, ["recall", "test query"])
        assert result.exit_code == 0
        assert "seed" in result.output

    def test_json(self, runner, mock_store):
        result = runner.invoke(cli, ["recall", "test", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) >= 1


class TestGet:
    def test_found(self, runner, mock_store):
        result = runner.invoke(cli, ["get", "test"])
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_not_found(self, runner, mock_store):
        mock_store.get.return_value = None
        result = runner.invoke(cli, ["get", "nonexistent"])
        assert result.exit_code != 0

    def test_json(self, runner, mock_store):
        result = runner.invoke(cli, ["get", "test", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "test"


class TestList:
    def test_basic(self, runner, mock_store):
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "Alpha" in result.output

    def test_json(self, runner, mock_store):
        result = runner.invoke(cli, ["list", "--json"])
        data = json.loads(result.output)
        assert len(data) >= 1


class TestDelete:
    def test_requires_confirm(self, runner, mock_store):
        result = runner.invoke(cli, ["delete", "test"])
        assert result.exit_code != 0
        assert "confirm" in result.output.lower()

    def test_with_confirm(self, runner, mock_store):
        result = runner.invoke(cli, ["delete", "test", "--confirm"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_not_found(self, runner, mock_store):
        mock_store.delete.return_value = False
        result = runner.invoke(cli, ["delete", "gone", "--confirm"])
        assert result.exit_code != 0


class TestSearch:
    def test_basic(self, runner, mock_store):
        result = runner.invoke(cli, ["search", "test"])
        assert result.exit_code == 0
        assert "Alpha" in result.output

    def test_json(self, runner, mock_store):
        result = runner.invoke(cli, ["search", "test", "--json"])
        data = json.loads(result.output)
        assert len(data) >= 1
