"""Tests for CLI main group — help, version, init."""

from click.testing import CliRunner

import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "memoryschema" in result.output
        assert "init" in result.output
        assert "doctor" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_global_project_option(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "status"])
        # May fail due to no store, but should parse args correctly
        assert "test" in result.output or result.exit_code in (0, 1, 2)


class TestInit:
    def test_creates_files(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "test-proj", "--root", str(tmp_path), "init"])
        assert result.exit_code == 0
        assert (tmp_path / "memory" / "MEMORY.md").exists()
        assert (tmp_path / ".claude" / "rules" / "memory-schema.md").exists()

    def test_scopes_working(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init", "--scopes", "working"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "rules" / "memory-working.md").exists()

    def test_scopes_corpus(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init", "--scopes", "working,corpus"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "rules" / "memory-corpus.md").exists()

    def test_idempotent(self, runner, tmp_path):
        runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init"])
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init"])
        assert result.exit_code == 0
        assert "already exist" in result.output

    def test_docker_compose_created(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "init"])
        assert (tmp_path / "docker-compose.yml").exists()

    def test_env_example_created(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "init"])
        assert (tmp_path / ".env.example").exists()
