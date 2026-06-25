"""Tests for CLI index, embed, associations commands."""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestIndex:
    def test_index_basic(self, runner, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "test.md").write_text("""<memory:entity schema="2" name="test">
  <memory:description>Test</memory:description>
</memory:entity>""")
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "index"])
        assert result.exit_code == 0
        assert "Indexed" in result.output


class TestEmbed:
    def test_coverage(self, runner, tmp_path):
        mock_store = MagicMock()
        mock_store.list_all.return_value = [
            {"name": "a", "embedding": [0.1]},
            {"name": "b"},
        ]
        with patch("memoryschema.cli.index_cmd._get_store", return_value=mock_store):
            result = runner.invoke(cli, ["--root", str(tmp_path), "embed", "--coverage"])
        assert result.exit_code == 0
        assert "50.0%" in result.output

    def test_requires_prefix_or_all(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "embed"])
        assert result.exit_code != 0


class TestAssociations:
    def test_show(self, runner, tmp_path):
        mock_store = MagicMock()
        mock_store.list_all.return_value = [
            {"name": "a", "associations": [{"name": "b", "score": 0.9}]},
            {"name": "b", "associations": [{"name": "a", "score": 0.9}]},
        ]
        with patch("memoryschema.cli.index_cmd._get_store", return_value=mock_store):
            result = runner.invoke(cli, ["--root", str(tmp_path), "associations"])
        assert result.exit_code == 0
        assert "2" in result.output

    def test_json(self, runner, tmp_path):
        mock_store = MagicMock()
        mock_store.list_all.return_value = []
        with patch("memoryschema.cli.index_cmd._get_store", return_value=mock_store):
            result = runner.invoke(cli, ["--root", str(tmp_path), "associations", "--json"])
        data = json.loads(result.output)
        assert "with_associations" in data
