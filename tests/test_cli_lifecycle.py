"""Tests for CLI lifecycle commands — backup, restore, reset, clean, export, import."""

import json
import os
import tarfile
from unittest.mock import patch

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project structure."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "MEMORY.md").write_text("## Index\n")
    (mem / "test-entity.md").write_text("""<memory:entity schema="2" name="test-entity">
  <memory:description>Test</memory:description>
</memory:entity>""")
    store = mem / "store.jsonl"
    store.write_text('{"name":"test-entity","description":"Test"}\n')
    rules = tmp_path / ".claude" / "rules"
    rules.mkdir(parents=True)
    (rules / "memory-schema.md").write_text("# Rules")
    (tmp_path / "docker-compose.yml").write_text("services: {}")
    return tmp_path


class TestBackup:
    def test_jsonl_only(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "backup", "--jsonl-only"])
        assert result.exit_code == 0
        assert "Backed up" in result.output

    def test_files_only(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "backup", "--files-only"])
        assert result.exit_code == 0
        assert "Backed up" in result.output

    def test_full_backup(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "backup"])
        assert result.exit_code == 0
        assert "Backup" in result.output


class TestReset:
    def test_requires_confirm(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "reset"])
        assert result.exit_code != 0
        assert "confirm" in result.output.lower()

    def test_store_only(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "reset", "--store-only", "--confirm"])
        assert result.exit_code == 0
        assert not (project_dir / "memory" / "store.jsonl").exists()

    def test_working_memory_only(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "reset", "--working-memory-only", "--confirm"])
        assert result.exit_code == 0
        assert (project_dir / "memory" / "MEMORY.md").exists()  # Preserved
        assert not (project_dir / "memory" / "test-entity.md").exists()  # Deleted


class TestClean:
    def test_dry_run(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "clean", "--dry-run"])
        assert result.exit_code == 0
        assert "Will remove" in result.output
        assert "dry run" in result.output.lower()
        # Nothing actually removed
        assert (project_dir / "memory").exists()

    def test_requires_confirm(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "clean"])
        assert result.exit_code != 0

    def test_with_confirm(self, runner, project_dir):
        with patch("subprocess.run"):
            result = runner.invoke(cli, ["--root", str(project_dir), "clean", "--confirm"])
        assert result.exit_code == 0
        assert "Clean complete" in result.output


class TestExport:
    def test_jsonl_format(self, runner, project_dir):
        mock_store = type('MockStore', (), {
            'list_all': lambda self: [{"name": "a", "description": "A"}],
        })()
        with patch("memoryschema.store.get_store", return_value=mock_store):
            output = str(project_dir / "export.jsonl")
            result = runner.invoke(cli, ["--root", str(project_dir), "export", "--format", "jsonl", "--output", output])
        assert result.exit_code == 0
        assert os.path.exists(output)

    def test_tar_format(self, runner, project_dir):
        output = str(project_dir / "export.tar.gz")
        result = runner.invoke(cli, ["--root", str(project_dir), "export", "--format", "tar", "--output", output])
        assert result.exit_code == 0
        assert os.path.exists(output)


class TestImport:
    def test_import_jsonl(self, runner, project_dir):
        # Create a JSONL file to import
        import_file = project_dir / "import.jsonl"
        import_file.write_text('{"name":"imported","schema":2,"description":"Imported entity"}\n')
        result = runner.invoke(cli, ["--root", str(project_dir), "import", str(import_file), "--format", "jsonl"])
        assert result.exit_code == 0
        assert "Imported" in result.output
