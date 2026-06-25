"""Tests for CLI voyage commands (mocked Voyage AI)."""

import json
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestVoyageStatus:
    def test_no_key(self, runner, tmp_path, monkeypatch):
        monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
        result = runner.invoke(cli, ["--root", str(tmp_path), "voyage", "status"])
        assert result.exit_code == 0
        assert "NOT SET" in result.output

    def test_with_key_json(self, runner, tmp_path, monkeypatch):
        monkeypatch.setenv("VOYAGE_API_KEY", "voy-test123")
        with patch("memoryschema.embeddings.embed_text", return_value=[0.1] * 1024):
            result = runner.invoke(cli, ["--root", str(tmp_path), "voyage", "status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["api_key_set"] is True


class TestVoyageTest:
    def test_no_key(self, runner, tmp_path, monkeypatch):
        monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
        result = runner.invoke(cli, ["--root", str(tmp_path), "voyage", "test", "hello"])
        assert result.exit_code != 0
        assert "VOYAGE_API_KEY" in result.output

    def test_with_key(self, runner, tmp_path, monkeypatch):
        monkeypatch.setenv("VOYAGE_API_KEY", "voy-test123")
        with patch("memoryschema.embeddings.embed_text", return_value=[0.1] * 1024):
            result = runner.invoke(cli, ["--root", str(tmp_path), "voyage", "test", "hello world"])
        assert result.exit_code == 0
        assert "Dimensions: 1024" in result.output


class TestVoyageHelp:
    def test_group_help(self, runner):
        result = runner.invoke(cli, ["voyage", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output
        assert "test" in result.output
