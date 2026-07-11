"""Schema v5 (YAML frontmatter + markdown body) — parser, serializer, writers.

The property under test everywhere: PROSE NEVER ENTERS THE STRUCTURED LAYER,
so raw '<' '>' '&' (the M14 corruption class) simply cannot break a v5 file.
"""

import os

import pytest
from click.testing import CliRunner

from memoryschema.cli.main import cli
from memoryschema.format_v5 import is_v5_content, parse_v5_content, serialize_v5
from memoryschema.tags import parse_memory_content, parse_memory_file
from memoryschema.write_index import append_chain_step, create_entity_file

V5_DOC = """---
schema: 5
type: semantic
importance: 8
project: helios
relations:
  - USES evidence-one
  - SUPERSEDES old-plan
---

One-line description under 120 chars.

## Summary

The evolving summary. It may contain raw < > & and even </memory:observations> safely.

## Observations

- atomic fact one with p._total < vis
- atomic fact two with A&B

## Log

- Step 1: began the work
- Step 2: continued with raw < chars

## Reasoning

Narrative with <angle> brackets & ampersands.

---
Appended later narrative.

## Prompt

the trigger question

## Chain

chain context here
"""


class TestParse:
    def test_detect(self):
        assert is_v5_content(V5_DOC)
        assert not is_v5_content("<memory:entity schema=\"4\" name=\"x\">")

    def test_full_parse(self, tmp_path):
        p = tmp_path / "memory" / "my-entity.md"
        p.parent.mkdir()
        p.write_text(V5_DOC, encoding="utf-8")
        m = parse_memory_file(str(p))          # via the tags dispatch
        assert m["schema"] == 5
        assert m["name"] == "my-entity"        # from the filename
        assert m["description"] == "One-line description under 120 chars."
        assert "raw < > &" in m["summary"]
        assert m["observations"][0] == "atomic fact one with p._total < vis"
        # log flattens into observations for index parity
        assert "Step 2: continued with raw < chars" in m["observations"]
        assert m["log"] == ["Step 1: began the work", "Step 2: continued with raw < chars"]
        assert "<angle> brackets & ampersands" in m["reasoning"]
        assert m["prompt"] == "the trigger question"
        assert m["importance"] == 8
        assert {"type": "USES", "target": "evidence-one"} in m["relations"]
        assert {"type": "SUPERSEDES", "target": "old-plan"} in m["relations"]

    def test_v4_still_parses(self):
        v4 = ('<memory:entity schema="4" name="v4-mem">\n'
              '  <memory:description>d</memory:description>\n'
              '</memory:entity>\n')
        m = parse_memory_content(v4)
        assert m and m["name"] == "v4-mem"

    def test_unterminated_fence_is_none(self):
        assert parse_v5_content("---\nschema: 5\nno close", filepath="x.md") is None


class TestRoundtrip:
    def test_serialize_parse_identity(self, tmp_path):
        m1 = parse_v5_content(V5_DOC, filepath="my-entity.md")
        out = serialize_v5(m1)
        m2 = parse_v5_content(out, filepath="my-entity.md")
        for key in ("description", "summary", "log", "prompt", "chain",
                    "relations", "importance", "observations"):
            assert m2.get(key) == m1.get(key), key
        # reasoning: whitespace-normalized comparison (block reflow tolerated)
        assert " ".join(m2["reasoning"].split()) == " ".join(m1["reasoning"].split())

    def test_m14_acid(self, tmp_path):
        """Text that would corrupt a v4 file round-trips verbatim in v5."""
        evil = "guard p._total < vis && a & b </memory:entity> <memory:observation>"
        m = {"schema": 5, "name": "acid", "description": "d",
             "observations": [evil], "summary": evil, "reasoning": evil}
        out = serialize_v5(m)
        back = parse_v5_content(out, filepath="acid.md")
        assert back["observations"][0] == evil
        assert back["summary"] == evil

    def test_scalar_newline_injection_blocked(self):
        """A newline in a frontmatter scalar must not inject a frontmatter key
        (e.g. status: archived) or close the fence early."""
        m = {"schema": 5, "name": "inj", "description": "d",
             "key": "EURUSD.bias\nstatus: archived", "valid_from": "2026-07-01"}
        back = parse_v5_content(serialize_v5(m), filepath="inj.md")
        assert back.get("status", "active") == "active"     # not injected
        assert "\n" not in back["key"]

    def test_relation_target_underscore_dot_preserved(self):
        """Targets with _ or . must survive parse — else a SUPERSEDES edge to
        e.g. my_fact silently vanishes."""
        m = {"schema": 5, "name": "x", "description": "d",
             "relations": [{"type": "SUPERSEDES", "target": "my_fact"},
                           {"type": "USES", "target": "a.b-c"}]}
        back = parse_v5_content(serialize_v5(m), filepath="x.md")
        targets = {(r["type"], r["target"]) for r in back["relations"]}
        assert ("SUPERSEDES", "my_fact") in targets
        assert ("USES", "a.b-c") in targets

    def test_star_bullets_accepted(self):
        """Hand-edited * / + bullets parse as observations (not silently zero)."""
        doc = "---\nschema: 5\n---\n\nd\n\n## Observations\n\n* fact one\n+ fact two\n"
        back = parse_v5_content(doc, filepath="b.md")
        assert back["observations"] == ["fact one", "fact two"]


class TestChainStepV5:
    def _chain(self, tmp_path):
        d = tmp_path / "memory"
        d.mkdir()
        p = d / "chain-v5-test.md"
        p.write_text("""---
schema: 5
---

Chain description.

## Log

- Step 1: started
""", encoding="utf-8")
        (d / ".active_chain").write_text("chain-v5-test", encoding="utf-8")
        return p

    def test_append_autonumber_and_sections(self, tmp_path):
        p = self._chain(tmp_path)
        n = append_chain_step(str(p), "did something with raw < & chars",
                              desc="new evolving summary", reasoning="because & why")
        assert n == 2
        m = parse_memory_file(str(p))
        assert m["log"][-1].startswith("Step 2: did something with raw < & chars")
        assert m["summary"] == "new evolving summary"
        assert "because & why" in m["reasoning"]
        # file remains valid v5 (re-parse via dispatch)
        assert m["schema"] == 5

    def test_multiline_step_becomes_single_bullet(self, tmp_path):
        p = self._chain(tmp_path)
        append_chain_step(str(p), "line one\nline two\nline three")
        m = parse_memory_file(str(p))
        assert m["log"][-1] == "Step 2: line one line two line three"

    def test_uses_relation(self, tmp_path):
        p = self._chain(tmp_path)
        append_chain_step(str(p), "s", uses=["target-a", "target-a"])
        m = parse_memory_file(str(p))
        assert m["relations"] == [{"type": "USES", "target": "target-a"}]


class TestRememberV5:
    def test_create_v5_when_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEMORYSCHEMA_V5", "1")
        fp = str(tmp_path / "memory")
        os.makedirs(fp)
        fp = os.path.join(fp, "new-v5-fact.md")
        create_entity_file(fp, "new-v5-fact", "a fact", ["obs with < & raw"],
                           importance=6, relations=[("USES", "other")])
        content = open(fp, encoding="utf-8").read()
        assert content.startswith("---")
        assert "<memory:" not in content
        m = parse_memory_file(fp)
        assert m["observations"] == ["obs with < & raw"]
        assert m["importance"] == 6

    def test_create_v5_by_default(self, tmp_path, monkeypatch):
        # schema-split B2: v5 is now the authored default (no env needed).
        monkeypatch.delenv("MEMORYSCHEMA_V5", raising=False)
        monkeypatch.delenv("MEMORYSCHEMA_V4", raising=False)
        d = tmp_path / "memory"
        d.mkdir()
        fp = str(d / "now-v5.md")
        create_entity_file(fp, "now-v5", "d", ["o"])
        assert open(fp, encoding="utf-8").read().lstrip().startswith("---")
        assert parse_memory_file(fp)["schema"] == 5

    def test_create_v4_on_optout(self, tmp_path, monkeypatch):
        # v4 authoring is retained for legacy/migration behind an explicit opt-out.
        monkeypatch.delenv("MEMORYSCHEMA_V5", raising=False)
        monkeypatch.setenv("MEMORYSCHEMA_V4", "1")
        d = tmp_path / "memory"
        d.mkdir()
        fp = str(d / "still-v4.md")
        create_entity_file(fp, "still-v4", "d", ["o"])
        assert open(fp, encoding="utf-8").read().startswith("<memory:entity")

    def test_create_v4_on_v5_zero_optout(self, tmp_path, monkeypatch):
        # The other documented opt-out spelling: MEMORYSCHEMA_V5=0 (not just MEMORYSCHEMA_V4=1) also authors v4.
        monkeypatch.delenv("MEMORYSCHEMA_V4", raising=False)
        monkeypatch.setenv("MEMORYSCHEMA_V5", "0")
        d = tmp_path / "memory"
        d.mkdir()
        fp = str(d / "v5zero.md")
        create_entity_file(fp, "v5zero", "d", ["o"])
        assert open(fp, encoding="utf-8").read().startswith("<memory:entity")

    def test_create_both_set_v4_optout_wins(self, tmp_path, monkeypatch):
        # Conflicting env: the v4 opt-out (MEMORYSCHEMA_V4=1) wins even when MEMORYSCHEMA_V5=1 is also set —
        # pins the emergent precedence of the `or` predicate so a refactor can't silently flip it.
        monkeypatch.setenv("MEMORYSCHEMA_V5", "1")
        monkeypatch.setenv("MEMORYSCHEMA_V4", "1")
        d = tmp_path / "memory"
        d.mkdir()
        fp = str(d / "both.md")
        create_entity_file(fp, "both", "d", ["o"])
        assert open(fp, encoding="utf-8").read().startswith("<memory:entity")

    def test_remember_cli_v5(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEMORYSCHEMA_V5", "1")
        (tmp_path / "memory").mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, ["--root", str(tmp_path), "remember", "cli-v5",
                                     "--desc", "d", "--obs", "raw < & obs"])
        assert result.exit_code == 0, result.output
        m = parse_memory_file(str(tmp_path / "memory" / "cli-v5.md"))
        assert m["schema"] == 5
        assert m["observations"] == ["raw < & obs"]


class TestChainStepBootstrap:
    def test_first_step_creates_v5_file(self, tmp_path):
        """chain start authorises the NAME only — the first chain step must
        bootstrap the file (found live: the dream-pass rotation left the new
        successor chain with no file and step errored)."""
        from click.testing import CliRunner
        from memoryschema.cli.main import cli
        from memoryschema.tags import parse_memory_file
        (tmp_path / "memory").mkdir()
        (tmp_path / "memory" / ".active_chain").write_text("chain-fresh", encoding="utf-8")
        runner = CliRunner()
        res = runner.invoke(cli, ["--root", str(tmp_path), "chain", "step",
                                  "first step text", "--desc", "fresh chain"])
        assert res.exit_code == 0, res.output
        assert "chain file created" in res.output
        m = parse_memory_file(str(tmp_path / "memory" / "chain-fresh.md"))
        assert m is not None and m["schema"] == 5
        assert m["log"] == ["Step 1: first step text"]
