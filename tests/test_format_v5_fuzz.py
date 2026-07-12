"""Malformed-LLM-output battery for the v5 parser (the module's single point of failure).

The parser is Postel-liberal / the validator is strict: every case here asserts the outcome is
**parse-clean or LOUD** — never a silent structural drop. These are regressions for the two
silent-truncation defects (relations-mode severing + unknown-section discard) plus the
no-silent-shrink writer guard.
"""

import os

from memoryschema.format_v5 import parse_v5_content, serialize_v5
from memoryschema.validator import validate
from memoryschema.write_index import append_chain_step, create_entity_file


def _rels(mem):
    return [(r["type"], r["target"]) for r in (mem.get("relations") or [])]


# ── relations mode must not sever on a stray non-relation line ────────────────────────────────────
def test_nested_bullet_inside_relations_does_not_drop_the_rest():
    f = """---
schema: 5
relations:
  - USES a-mem
  - a stray freeform bullet with too many words
  - SUPERSEDES b-mem
---

Desc.
"""
    mem = parse_v5_content(f, filepath="e.md")
    # the SUPERSEDES edge after the stray line MUST survive (pre-fix it was silently dropped)
    assert ("SUPERSEDES", "b-mem") in _rels(mem)
    assert ("USES", "a-mem") in _rels(mem)


def test_comment_and_blank_line_inside_relations_survive():
    f = """---
schema: 5
relations:
  - USES a-mem

  # a comment mid-block
  - INFORMS c-mem
---

Desc.
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert ("USES", "a-mem") in _rels(mem)
    assert ("INFORMS", "c-mem") in _rels(mem)


def test_top_level_scalar_after_relations_still_exits_the_block():
    # a genuine column-0 `key:` scalar AFTER relations: must still be captured as a scalar
    f = """---
schema: 5
relations:
  - USES a-mem
importance: 9
---

Desc.
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert ("USES", "a-mem") in _rels(mem)
    assert mem.get("importance") == 9


# ── lowercase relation type: parse-liberally, validate-strictly ───────────────────────────────────
def test_lowercase_relation_type_parses_then_validator_flags_r2():
    f = """---
schema: 5
relations:
  - uses a-mem
---

A short description.
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert ("uses", "a-mem") in _rels(mem), "lowercase type must PARSE, not vanish"
    errors = validate(f, filepath="e.md")
    assert any(rid == "R2" for rid, _ in errors), "the validator must flag the non-canonical type loudly"


# ── unknown / duplicate sections preserved verbatim ───────────────────────────────────────────────
def test_unknown_section_roundtrips_verbatim():
    f = """---
schema: 5
relations:
  - USES a-mem
---

Lead desc.

## Summary
The summary.

## Custom Analysis
Bespoke line one.
Line two.

## Observations
- fact one
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert mem.get("extra_sections") == [("Custom Analysis", "Bespoke line one.\nLine two.")]
    out = serialize_v5(mem)
    assert "## Custom Analysis" in out
    re_mem = parse_v5_content(out, filepath="e.md")
    assert re_mem.get("extra_sections") == mem.get("extra_sections")
    assert _rels(re_mem) == _rels(mem)


def test_duplicate_sections_merge_without_dropping_content():
    f = """---
schema: 5
---

Desc.

## Observations
- first

## Observations
- second
"""
    mem = parse_v5_content(f, filepath="e.md")
    # duplicate headings MERGE (documented) — neither bullet is lost
    assert "first" in mem["observations"] and "second" in mem["observations"]


def test_stray_mid_body_fence_is_body_content_not_corruption():
    f = """---
schema: 5
---

Desc.

## Reasoning
Some reasoning.

---

More reasoning after a horizontal rule.
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert mem is not None, "a mid-body `---` must not break the parse"
    assert "More reasoning" in (mem.get("reasoning") or "")


def test_full_roundtrip_identity_with_unknown_section_and_relations():
    f = """---
schema: 5
type: procedural
importance: 6
relations:
  - USES a-mem
  - SUPERSEDES b-mem
---

Lead paragraph.

## Summary
Sum.

## Decision Log
Kept for the record.

## Observations
- one
- two
"""
    mem = parse_v5_content(f, filepath="e.md")
    twice = parse_v5_content(serialize_v5(mem), filepath="e.md")
    assert twice.get("extra_sections") == mem.get("extra_sections")
    assert _rels(twice) == _rels(mem)
    assert twice["observations"] == mem["observations"]
    assert twice.get("importance") == 6 and twice.get("type") == "procedural"


# ── the writer self-check: an append preserves relations + unknown sections ────────────────────────
def test_append_chain_step_preserves_relations_and_unknown_sections(tmp_path):
    p = tmp_path / "chain-x.md"
    p.write_text(
        """---
schema: 5
type: procedural
relations:
  - USES a-mem
  - SUPERSEDES b-mem
---

A chain.

## Custom Section
Must survive the append.

## Log
- Step 1: first
""",
        encoding="utf-8",
    )
    append_chain_step(str(p), "second thing happened")
    mem = parse_v5_content(p.read_text(encoding="utf-8"), filepath=str(p))
    assert ("USES", "a-mem") in _rels(mem) and ("SUPERSEDES", "b-mem") in _rels(mem)
    assert mem.get("extra_sections") == [("Custom Section", "Must survive the append.")]
    assert any(str(s).startswith("Step 2:") for s in (mem.get("log") or []))
