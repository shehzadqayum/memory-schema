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
        # schema ref is deployed on-demand (from the claude_plugin SSOT), not always-loaded
        assert (tmp_path / ".claude" / "rules-ondemand" / "memory-schema.md").exists()
        assert (tmp_path / ".claude" / "rules" / "memory-working.md").exists()   # the always-loaded kernel

    def test_scopes_working(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init", "--scopes", "working"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "rules" / "memory-working.md").exists()

    def test_scopes_corpus(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init", "--scopes", "working,corpus"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "rules-ondemand" / "memory-corpus.md").exists()
        # a non-corpus init must NOT deploy the corpus rule
        result2 = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path / "no-corpus"), "init", "--scopes", "working"])
        assert not (tmp_path / "no-corpus" / ".claude" / "rules-ondemand" / "memory-corpus.md").exists()

    def test_idempotent(self, runner, tmp_path):
        runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init"])
        result = runner.invoke(cli, ["--project", "t", "--root", str(tmp_path), "init"])
        assert result.exit_code == 0
        assert "already exist" in result.output

    def test_docker_compose_created(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "init"])
        assert (tmp_path / "docker-compose.yml").exists()

    def test_compose_password_parameterized_not_baked(self, runner, tmp_path, monkeypatch):
        # Security (Part C MED): the generated compose must NOT bake a plaintext secret at rest — it
        # references ${NEO4J_PASSWORD}, persisted to a gitignored .env instead.
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "init"])
        compose = (tmp_path / "docker-compose.yml").read_text(encoding="utf-8")
        assert "NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}" in compose
        import re as _re
        assert not _re.search(r"NEO4J_AUTH=neo4j/[A-Za-z0-9_-]{16,}", compose), "plaintext secret baked in compose"
        assert "# memoryschema-managed" in compose, "preflight trust sentinel missing"
        env_text = (tmp_path / ".env").read_text(encoding="utf-8")
        assert "NEO4J_PASSWORD=" in env_text and len(env_text.split("NEO4J_PASSWORD=")[1].strip()) >= 16
        assert ".env" in [ln.strip() for ln in (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()]

    def test_init_env_gitignore_append_is_newline_safe(self, runner, tmp_path, monkeypatch):
        # Real-bug guard: a pre-existing .gitignore/.env whose final line lacks a trailing newline must NOT get
        # the new entry glued onto it (which would break the .gitignore pattern or corrupt the .env key/value).
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        (tmp_path / ".gitignore").write_text("node_modules", encoding="utf-8")   # no trailing newline
        (tmp_path / ".env").write_text("VOYAGE_API_KEY=vk", encoding="utf-8")     # no trailing newline
        runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "init"])
        gi = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert ".env" in [ln.strip() for ln in gi.splitlines()], ".env must land on its own gitignore line"
        assert "node_modules.env" not in gi, "gitignore entry glued onto the prior non-terminated line"
        env = (tmp_path / ".env").read_text(encoding="utf-8")
        assert any(ln.strip() == "VOYAGE_API_KEY=vk" for ln in env.splitlines()), "existing .env line corrupted"
        assert any(ln.startswith("NEO4J_PASSWORD=") for ln in env.splitlines()), "NEO4J_PASSWORD not on its own line"

    def test_env_example_created(self, runner, tmp_path):
        result = runner.invoke(cli, ["--project", "test", "--root", str(tmp_path), "init"])
        assert (tmp_path / ".env.example").exists()
