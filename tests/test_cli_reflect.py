"""Tests for CLI reflect command."""

import json
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestReflect:
    def test_dry_run(self, runner, tmp_path):
        mock_result = {'clusters': 2, 'summaries': 0, 'archived': 0, 'dry_run': True}
        with patch("memoryschema.consolidation.reflect", return_value=mock_result):
            with patch("memoryschema.store.get_store"):
                result = runner.invoke(cli, ["--root", str(tmp_path), "reflect", "--dry-run"])
        assert result.exit_code == 0
        assert "Clusters:   2" in result.output
        assert "dry run" in result.output

    def test_json_output(self, runner, tmp_path):
        mock_result = {'clusters': 1, 'summaries': 1, 'archived': 3, 'dry_run': False}
        with patch("memoryschema.consolidation.reflect", return_value=mock_result):
            with patch("memoryschema.store.get_store"):
                result = runner.invoke(cli, ["--root", str(tmp_path), "reflect", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['clusters'] == 1
        assert data['summaries'] == 1
        assert data['archived'] == 3

    def test_no_episodic_entries(self, runner, tmp_path):
        mock_result = {'clusters': 0, 'summaries': 0, 'archived': 0, 'dry_run': False}
        with patch("memoryschema.consolidation.reflect", return_value=mock_result):
            with patch("memoryschema.store.get_store"):
                result = runner.invoke(cli, ["--root", str(tmp_path), "reflect"])
        assert result.exit_code == 0
        assert "Clusters:   0" in result.output

    def test_with_project_option(self, runner, tmp_path):
        mock_result = {'clusters': 1, 'summaries': 1, 'archived': 2, 'dry_run': False}
        with patch("memoryschema.consolidation.reflect", return_value=mock_result) as mock_fn:
            with patch("memoryschema.store.get_store"):
                result = runner.invoke(cli, ["--root", str(tmp_path), "reflect", "--project", "org.team"])
        assert result.exit_code == 0
        mock_fn.assert_called_once()
        call_kwargs = mock_fn.call_args
        assert call_kwargs[1]['project'] == 'org.team' or call_kwargs.kwargs.get('project') == 'org.team'

    def test_help(self, runner):
        result = runner.invoke(cli, ["reflect", "--help"])
        assert result.exit_code == 0
        assert "Cluster episodic" in result.output
        assert "--dry-run" in result.output
        assert "--min-cluster" in result.output
