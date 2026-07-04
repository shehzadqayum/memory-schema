"""Tests for the deterministic write path: write_index + chain step + remember CLI.

The core property under test: PLAIN TEXT IN, VALID ENTITY OUT — raw '<'/'&'
in prose (the M14 corruption class) must be impossible on this path.
"""

import os

import pytest
from click.testing import CliRunner

from memoryschema.cli.main import cli
from memoryschema.tags import parse_memory_file
from memoryschema.write_index import (
    append_chain_step,
    create_entity_file,
    escape_text,
    index_memory,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    (tmp_path / "memory").mkdir()
    return tmp_path


CHAIN_NAME = "chain-test-topic"

CHAIN_V4 = """<memory:entity schema="4" name="chain-test-topic" type="semantic" importance="7">
  <memory:description>Initial summary</memory:description>
  <memory:observations>
    <memory:observation>Step 1: began the investigation</memory:observation>
  </memory:observations>
  <memory:prompt>the trigger question</memory:prompt>
  <memory:reasoning>Initial narrative.</memory:reasoning>
  <memory:relations>
    <memory:relation target="some-evidence" type="USES"/>
  </memory:relations>
</memory:entity>
"""


def _write_chain(project_dir, activate=True):
    path = project_dir / "memory" / (CHAIN_NAME + ".md")
    path.write_text(CHAIN_V4, encoding="utf-8")
    if activate:
        (project_dir / "memory" / ".active_chain").write_text(CHAIN_NAME, encoding="utf-8")
    return path


class TestEscaping:
    def test_escapes_lt_amp(self):
        assert escape_text("p._total < vis && x") == "p._total &lt; vis &amp;&amp; x"

    def test_m14_prose_survives_roundtrip(self, project_dir):
        """The exact M14 class: raw '<' and '&' in step prose must produce a
        file that still parses, with the text preserved verbatim."""
        path = _write_chain(project_dir)
        evil = "guard is p._total < vis; also A&B and </memory:observations> quoted"
        n = append_chain_step(str(path), evil)
        assert n == 2
        mem = parse_memory_file(str(path))
        assert mem is not None, "file must still parse after an evil append"
        assert any("p._total < vis" in o for o in mem["observations"])
        assert any("</memory:observations> quoted" in o for o in mem["observations"])


class TestAppendChainStep:
    def test_auto_numbering(self, project_dir):
        path = _write_chain(project_dir)
        assert append_chain_step(str(path), "second thing") == 2
        assert append_chain_step(str(path), "third thing") == 3
        mem = parse_memory_file(str(path))
        assert mem["observations"][1].startswith("Step 2:")
        assert mem["observations"][2].startswith("Step 3:")

    def test_explicit_step_prefix_kept(self, project_dir):
        path = _write_chain(project_dir)
        append_chain_step(str(path), "Conclusion: it works")
        mem = parse_memory_file(str(path))
        assert mem["observations"][-1] == "Conclusion: it works"

    def test_desc_replace_and_reasoning_append(self, project_dir):
        path = _write_chain(project_dir)
        append_chain_step(str(path), "s", desc="New summary with < raw",
                          reasoning="More narrative & analysis")
        mem = parse_memory_file(str(path))
        assert mem["description"] == "New summary with < raw"
        assert "Initial narrative." in mem["reasoning"]
        assert "More narrative & analysis" in mem["reasoning"]
        assert "---" in mem["reasoning"]

    def test_uses_relation_added_and_deduped(self, project_dir):
        path = _write_chain(project_dir)
        append_chain_step(str(path), "s", uses=["new-target", "some-evidence"])
        mem = parse_memory_file(str(path))
        targets = [r["target"] for r in mem["relations"]]
        assert targets.count("new-target") == 1
        assert targets.count("some-evidence") == 1  # deduped, not doubled

    def test_rollback_on_structural_failure(self, project_dir):
        path = _write_chain(project_dir)
        broken = CHAIN_V4.replace("</memory:observations>", "")  # no anchor
        path.write_text(broken, encoding="utf-8")
        with pytest.raises(ValueError):
            append_chain_step(str(path), "won't land")
        assert path.read_text(encoding="utf-8") == broken  # untouched


class TestCreateEntityFile:
    def test_creates_valid_entity_with_evil_text(self, project_dir):
        fp = str(project_dir / "memory" / "new-fact.md")
        create_entity_file(fp, "new-fact", "desc with < & raw",
                           ["obs one with <tags> & ampersands", "obs two"],
                           importance=6, relations=[("USES", "other-mem")])
        mem = parse_memory_file(fp)
        assert mem is not None
        assert mem["name"] == "new-fact"
        assert mem["description"] == "desc with < & raw"
        assert mem["observations"][0] == "obs one with <tags> & ampersands"

    def test_refuses_overwrite(self, project_dir):
        fp = str(project_dir / "memory" / "dup.md")
        create_entity_file(fp, "dup", "d", ["o"])
        with pytest.raises(FileExistsError):
            create_entity_file(fp, "dup", "d2", ["o2"])


class TestIndexMemory:
    def test_indexes_to_jsonl_and_rebuilds_l0(self, project_dir):
        path = _write_chain(project_dir)
        res = index_memory(str(path))
        assert res.ok
        assert "jsonl" in res.indexed_to
        store = project_dir / "memory" / "store.jsonl"
        assert store.exists() and CHAIN_NAME in store.read_text(encoding="utf-8")
        assert (project_dir / "memory" / "MEMORY.md").exists()

    def test_blocks_non_active_existing_entity(self, project_dir):
        path = _write_chain(project_dir)
        index_memory(str(path))  # first index (new entity — allowed)
        (project_dir / "memory" / ".active_chain").write_text("chain-other", encoding="utf-8")
        res = index_memory(str(path))
        assert not res.ok
        assert any("read-only" in e for e in res.errors)

    def test_corrupt_file_fails_loud(self, project_dir):
        path = project_dir / "memory" / "bad.md"
        path.write_text("<memory:entity schema=\"4\" name=\"bad\">\n"
                        "  <memory:description>raw < inside</memory:description>\n"
                        "</memory:entity>\n", encoding="utf-8")
        res = index_memory(str(path))
        assert not res.ok


class TestChainStepCLI:
    def test_step_end_to_end(self, runner, project_dir):
        _write_chain(project_dir)
        result = runner.invoke(cli, ["--root", str(project_dir), "chain", "step",
                                     "did a thing with p._total < vis", "--desc", "sum & more"])
        assert result.exit_code == 0, result.output
        assert "step 2 written" in result.output
        mem = parse_memory_file(str(project_dir / "memory" / (CHAIN_NAME + ".md")))
        assert mem is not None
        assert mem["description"] == "sum & more"

    def test_step_requires_active_chain(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "chain", "step", "text"])
        assert result.exit_code != 0
        assert "no active chain" in (result.output + str(result.stderr_bytes or b"")).lower() \
            or "no active chain" in result.output.lower()

    def test_step_stdin(self, runner, project_dir):
        _write_chain(project_dir)
        result = runner.invoke(cli, ["--root", str(project_dir), "chain", "step", "--stdin"],
                               input="long stdin text with < & raw chars\n")
        assert result.exit_code == 0, result.output
        mem = parse_memory_file(str(project_dir / "memory" / (CHAIN_NAME + ".md")))
        assert any("< & raw chars" in o for o in mem["observations"])


class TestRememberCLI:
    def test_remember_end_to_end(self, runner, project_dir):
        result = runner.invoke(cli, ["--root", str(project_dir), "remember", "fact-one",
                                     "--desc", "a fact", "--obs", "obs with < & evil",
                                     "--obs", "second obs", "--importance", "6"])
        assert result.exit_code == 0, result.output
        mem = parse_memory_file(str(project_dir / "memory" / "fact-one.md"))
        assert mem is not None
        assert mem["observations"][0] == "obs with < & evil"
        store = project_dir / "memory" / "store.jsonl"
        assert "fact-one" in store.read_text(encoding="utf-8")

    def test_remember_refuses_existing(self, runner, project_dir):
        runner.invoke(cli, ["--root", str(project_dir), "remember", "fact-dup",
                            "--desc", "d", "--obs", "o"])
        result = runner.invoke(cli, ["--root", str(project_dir), "remember", "fact-dup",
                                     "--desc", "d2", "--obs", "o2"])
        assert result.exit_code != 0


class TestGateNudges:
    def test_long_description_warns_for_standalone(self, project_dir):
        from memoryschema.write_gate import gate_pipeline
        res = gate_pipeline({"name": "standalone-x", "description": "y" * 200,
                             "observations": ["o"]})
        assert any("<=120" in w for w in res.warnings)

    def test_chain_exempt_from_desc_warning(self, project_dir):
        from memoryschema.write_gate import gate_pipeline
        res = gate_pipeline({"name": "chain-x", "description": "y" * 200,
                             "observations": ["o"]})
        assert not any("<=120" in w for w in res.warnings)
