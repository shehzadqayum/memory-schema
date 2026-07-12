"""Malformed-LLM-output battery for the v5 parser (the module's single point of failure).

The parser is Postel-liberal / the validator is strict: every case here asserts the outcome is
**parse-clean or LOUD** — never a silent structural drop. These are regressions for the two
silent-truncation defects (relations-mode severing + unknown-section discard) plus the
no-silent-shrink writer guard.
"""

import os

import pytest

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


def test_inline_comment_on_relation_line_does_not_drop_the_edge():
    # a YAML inline comment on a relation line must not silently drop the edge (esp. SUPERSEDES)
    f = """---
schema: 5
relations:
  - SUPERSEDES old-fact   # retired 2026-07
  - USES a-mem
---

Desc.
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert ("SUPERSEDES", "old-fact") in _rels(mem)
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


def test_fenced_heading_inside_unknown_section_does_not_fragment():
    # a `## Heading` inside a ``` code fence is CONTENT, not a section boundary — memory notes embed examples
    f = """---
schema: 5
---

Desc.

## Snippet
Example:
```md
## Inner Example
```
done
"""
    mem = parse_v5_content(f, filepath="e.md")
    assert [t for t, _ in (mem.get("extra_sections") or [])] == ["Snippet"], "must stay ONE section"
    body = dict(mem["extra_sections"])["Snippet"]
    assert "## Inner Example" in body and "done" in body
    out = serialize_v5(mem)
    assert out.count("## Inner Example") == 1
    assert parse_v5_content(out, filepath="e.md").get("extra_sections") == mem.get("extra_sections")


def test_append_desc_with_heading_line_is_refused_not_corrupted(tmp_path):
    # a multi-line --desc with a column-0 `## ` line would truncate ## Summary + spawn a phantom section;
    # the no-shrink guard must REFUSE (fail loud), not silently corrupt (title-superset would have masked it)
    p = tmp_path / "chain-y.md"
    p.write_text("---\nschema: 5\ntype: procedural\n---\n\nA chain.\n\n## Log\n- Step 1: first\n",
                 encoding="utf-8")
    original = p.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        append_chain_step(str(p), "second", desc="keep this\n## Note\ndropped tail")
    assert p.read_text(encoding="utf-8") == original      # file left unchanged


def test_append_reasoning_heading_matching_existing_section_is_refused(tmp_path):
    # injected `## Note` duplicating an existing unknown section: title set is unchanged, but content merges —
    # the content-aware equality check must still catch it (a title-only check would pass)
    p = tmp_path / "chain-z.md"
    p.write_text("---\nschema: 5\n---\n\nA chain.\n\n## Note\nfoo\n\n## Log\n- Step 1: first\n",
                 encoding="utf-8")
    original = p.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        append_chain_step(str(p), "second", reasoning="bar\n## Note\nbaz")
    assert p.read_text(encoding="utf-8") == original


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


def test_bom_prefixed_v5_dispatches_and_parses():
    from memoryschema.format_v5 import is_v5_content
    from memoryschema.tags import parse_memory_content
    f = "﻿---\nschema: 5\n---\n\nA BOM-prefixed entity.\n"
    assert is_v5_content(f), "dispatch must be BOM-tolerant (parse + guard already are)"
    mem = parse_memory_content(f, filepath="e.md")   # the DISPATCH path, not parse_v5_content directly
    assert mem is not None and mem["name"] == "e"


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
