"""Tests for CLI validate command."""

from click.testing import CliRunner
import pytest

from memoryschema.cli.main import cli


VALID_ENTITY = """<memory:entity schema="2" name="valid-test">
  <memory:description>A valid entity</memory:description>
</memory:entity>"""

INVALID_ENTITY = """<memory:entity schema="2" name="invalid-test">
</memory:entity>"""


@pytest.fixture
def runner():
    return CliRunner()


class TestValidate:
    def test_valid_file(self, runner, tmp_path):
        f = tmp_path / "valid-test.md"
        f.write_text(VALID_ENTITY)
        result = runner.invoke(cli, ["--root", str(tmp_path), "validate", str(f)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_invalid_file(self, runner, tmp_path):
        f = tmp_path / "invalid-test.md"
        f.write_text(INVALID_ENTITY)
        result = runner.invoke(cli, ["--root", str(tmp_path), "validate", str(f)])
        assert result.exit_code != 0
        assert "V6" in result.output

    def test_directory(self, runner, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "good.md").write_text(VALID_ENTITY.replace("valid-test", "good"))
        (mem / "bad.md").write_text(INVALID_ENTITY.replace("invalid-test", "bad"))
        result = runner.invoke(cli, ["--root", str(tmp_path), "validate", str(mem)])
        assert "errors" in result.output.lower() or "V6" in result.output

    def test_default_path(self, runner, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "entity.md").write_text(VALID_ENTITY.replace("valid-test", "entity"))
        result = runner.invoke(cli, ["--root", str(tmp_path), "validate"])
        assert result.exit_code == 0

    def test_json_output(self, runner, tmp_path):
        f = tmp_path / "valid-test.md"
        f.write_text(VALID_ENTITY)
        result = runner.invoke(cli, ["--root", str(tmp_path), "validate", str(f), "--json"])
        assert result.exit_code == 0

    def test_nonexistent_path(self, runner, tmp_path):
        result = runner.invoke(cli, ["--root", str(tmp_path), "validate", "/nonexistent"])
        assert result.exit_code != 0
