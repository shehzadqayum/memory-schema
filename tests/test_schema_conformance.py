"""Schema conformance — the harness conforms to entity_schema.py (the AUTHORITY).

The anti-drift bridge for the schema split. The code single-sources the grammar/enums (imports them from
`entity_schema`), so this does NOT assert tautological constant-equality; it asserts what can actually
regress: (i) single-source identity, (ii) BEHAVIOR — the validator + the v5 parser agree with the authority
grammar, (iii) the parse-liberally/validate-strictly contract, (iv) a representative CORPUS conforms. Spots
the harness does not yet honor are marked xfail/skip — the living Part-B follow-up worklist
(see memory: plan-memoryschema-schema-split). Hermetic: no read of any live `memory/` dir.
"""
import pytest

from memoryschema import entity_schema as SCH
from memoryschema import validator, config
from memoryschema.format_v5 import _REL_RE


# ── (i) single-source: one definition, imported (not copied) ──────────────────────────────────────
def test_enums_single_sourced_from_authority():
    assert config.VALID_TYPES is SCH.VALID_TYPES
    assert config.VALID_STATUSES is SCH.VALID_STATUSES
    assert config.VALID_RELATION_TYPES is SCH.VALID_RELATION_TYPES
    assert config.ALL_RELATION_TYPES is SCH.ALL_RELATION_TYPES
    assert config.SCHEMA_VERSION == SCH.SCHEMA_VERSION


def test_validator_grammar_is_the_authority():
    assert validator.KEBAB_CASE is SCH.NAME_RE   # not a re-introduced local regex


def test_relation_types_are_exactly_the_documented_set():
    assert SCH.VALID_RELATION_TYPES == frozenset(
        {'USES', 'MODIFIES', 'SUPERSEDES', 'DEPENDS_ON', 'INFORMS', 'CONTRADICTS', 'MITIGATES'})
    assert SCH.DEPRECATED_RELATION_TYPES == frozenset({'PARENT_OF', 'CHILD_OF'})
    assert SCH.ALL_RELATION_TYPES == SCH.VALID_RELATION_TYPES | SCH.DEPRECATED_RELATION_TYPES


# ── (ii) behavior: validator agrees with the authority grammar ────────────────────────────────────
VALID_NAMES = ['memory-schema', 'a', 'x1', 'bridge-timezone', 'a1-b2-c3', 'usd-strength-20260619']
INVALID_NAMES = ['Bad-Name', 'has_underscore', 'has.dot', 'trailing-', '-leading', 'has space', 'CAPS', '']


@pytest.mark.parametrize('name', VALID_NAMES)
def test_authority_accepts_valid_names(name):
    assert SCH.NAME_RE.match(name)


@pytest.mark.parametrize('name', INVALID_NAMES)
def test_authority_rejects_invalid_names(name):
    assert not SCH.NAME_RE.match(name)


@pytest.mark.parametrize('name', VALID_NAMES + INVALID_NAMES)
def test_validator_kebab_matches_authority(name):
    # the validator's kebab check (R3 target / Q1 name) is exactly the authority grammar
    assert bool(validator.KEBAB_CASE.match(name)) == bool(SCH.NAME_RE.match(name))


# ── (iii) parse-liberally / validate-strictly (Postel) ────────────────────────────────────────────
def test_parser_never_drops_an_authority_valid_target():
    # the v5 line parser must accept every authority-valid target (it MAY accept a wider set — a documented
    # superset — but must never reject a valid one, or a legal edge is silently lost on parse)
    for name in VALID_NAMES:
        assert _REL_RE.match(f'- USES {name}'), f'parser dropped valid target {name!r}'


def test_fact_key_grammar_is_distinct_from_name():
    assert SCH.KEY_RE.match('memory-schema.multi-space-status')   # dotted namespaces are keys-only
    assert not SCH.NAME_RE.match('memory-schema.multi-space-status')
    assert not SCH.KEY_RE.match('no-dots-here')                   # a key needs >= 2 segments


# ── (iv) corpus: representative entities conform (hermetic — inline fixtures, no live dir read) ────
def test_representative_corpus_conforms():
    for name in VALID_NAMES:
        assert SCH.NAME_RE.match(name), f'representative entity name {name!r} is not authority-valid'
    fixture_relation_lines = ['- USES memory-schema', '- SUPERSEDES bridge-timezone', '- INFORMS a1-b2-c3']
    for line in fixture_relation_lines:
        m = _REL_RE.match(line)
        assert m and m.group(1) in SCH.ALL_RELATION_TYPES


# ── (v) doc generation is stable + self-describing ────────────────────────────────────────────────
def test_render_reference_tables_reflects_the_authority():
    out = SCH.render_reference_tables()
    for rel in SCH.VALID_RELATION_TYPES:
        assert rel in out
    assert SCH.NAME_RE.pattern in out and SCH.KEY_RE.pattern in out
    assert 'v5' in out and all(f in out for f in SCH.FRONTMATTER_FIELDS)


# ── Part-B follow-up worklist (each flips to a passing test when its harness fix lands) ────────────
def test_b4_schema_version_reflects_current_format():
    """B4 (LANDED): SCHEMA_VERSION tracks the current authored format, not the legacy v4 marker. The v4-XML
    `schema=` attribute keeps its own distinct upper bound for the V10 range check."""
    assert SCH.SCHEMA_VERSION == SCH.CURRENT_ENTITY_FORMAT == 5
    assert SCH.V4_XML_SCHEMA_VERSION == 4 and SCH.V4_XML_SCHEMA_VERSION < SCH.SCHEMA_VERSION


def test_b1_v5_entities_are_validated():
    """B1 (LANDED): validate() dispatches on format — a v5 entity runs the real V/R/Q rules instead of the
    old spurious V1 'no entity'. Hermetic: inline content strings, no dir read."""
    from memoryschema import validator
    good = ("---\nschema: 5\nname: good-entity\ntype: semantic\nstatus: active\n---\n\n"
            "A well-formed v5 entity used as the clean fixture.\n\n"
            "## Observations\n- a fine observation\n")
    assert validator.validate(good, strict=True) == [], "a well-formed v5 entity must validate clean"
    # regression: it must NOT be reported as the XML V1 'no entity' (the pre-B1 bug)
    assert not any(r == 'V1' for r, _ in validator.validate(good)), "v5 must not trip the XML V1 rule"

    def rules(md):
        return {r for r, _ in validator.validate(md, strict=True)}

    assert 'Q1' in rules("---\nschema: 5\nname: Bad_Name\n---\n\nd\n\n## Observations\n- x\n")      # non-kebab name
    assert 'V11' in rules("---\nschema: 5\nname: e\nstatus: bogus\n---\n\nd\n\n## Observations\n- x\n")  # bad status
    assert 'Q2' in rules("---\nschema: 5\nname: e\n---\n\n" + ("word " * 40) + "\n\n## Observations\n- x\n")  # desc >120
    assert 'R2' in rules("---\nschema: 5\nname: e\nrelations:\n- FROBNICATE target-x\n---\n\nd\n")   # bad rel type
    assert 'R3' in rules("---\nschema: 5\nname: e\nrelations:\n- USES Bad_Target\n---\n\nd\n")       # non-kebab target
    assert 'V1' in rules("---\nschema: 5\nname: e\n## Observations\n- unterminated fence\n")         # corrupt v5
    assert 'R4' in rules("---\nschema: 5\nname: self-ref\nrelations:\n- USES self-ref\n---\n\nd\n")  # self-reference
    assert 'R5' in rules("---\nschema: 5\nname: e\nrelations:\n- USES target-x\n- USES target-x\n---\n\nd\n")  # dup
    # importance parity: a non-integer importance is flagged V5 in v5 exactly as v4 does (parser drops it silently)
    assert 'V5' in rules("---\nschema: 5\nname: e\nimportance: high\n---\n\nd\n\n## Observations\n- x\n")

    # Q6/Q7 operate on REAL observations, not chain `## Log` steps (the parser flattens log into observations)
    chain_md = ("---\nschema: 5\nname: e\n---\n\nd\n\n## Observations\n- one real observation\n\n## Log\n"
                + "".join(f"- Step {i}: did a thing\n" for i in range(1, 16)))
    assert 'Q6' not in rules(chain_md), "chain Log steps must not count toward the Q6 observation cap"
    many_obs = "---\nschema: 5\nname: e\n---\n\nd\n\n## Observations\n" + "".join(f"- obs {i}\n" for i in range(11))
    assert 'Q6' in rules(many_obs), "11 real observations must trip Q6"
    long_obs = "---\nschema: 5\nname: e\n---\n\nd\n\n## Observations\n- " + ("word " * 60) + "\n"
    assert 'Q7' in rules(long_obs), "a >50-word observation must trip Q7"


def test_b2_new_entities_default_to_v5(tmp_path, monkeypatch):
    """B2 (LANDED): create_entity_file authors v5 by default; legacy v4 only on explicit opt-out. Hermetic:
    a tmp dir, no backend."""
    monkeypatch.delenv("MEMORYSCHEMA_V5", raising=False)
    monkeypatch.delenv("MEMORYSCHEMA_V4", raising=False)
    from memoryschema.write_index import create_entity_file
    from memoryschema.tags import parse_memory_file
    d = tmp_path / "memory"
    d.mkdir()
    fp = str(d / "b2-default.md")
    create_entity_file(fp, "b2-default", "a default entity", ["o"])
    assert open(fp, encoding="utf-8").read().lstrip().startswith("---"), "default authored format must be v5"
    assert parse_memory_file(fp)["schema"] == 5
    # explicit opt-out still authors legacy v4 (retained for migration)
    monkeypatch.setenv("MEMORYSCHEMA_V4", "1")
    fp4 = str(d / "b2-optout.md")
    create_entity_file(fp4, "b2-optout", "a legacy entity", ["o"])
    assert open(fp4, encoding="utf-8").read().startswith("<memory:entity"), "opt-out must author v4"


def test_b3_malformed_v5_is_guarded_not_pruned(tmp_path):
    """B3 (LANDED): reconcile._parse_md treats a corrupt v5 entity as CORRUPTION — surfaced as `malformed`
    so reconcile aborts rather than prunes — while a plain non-entity frontmatter note is still skipped.
    Hermetic: a throwaway tmp dir, never the live memory/."""
    import os
    from memoryschema import reconcile
    mem = tmp_path
    # a corrupt v5 entity: declares `schema: 5` but the frontmatter fence is never closed -> parse fails
    (mem / "broken-v5.md").write_text(
        "---\nschema: 5\nname: broken-v5\ntype: semantic\n"
        "## Observations\n- the closing fence is missing so this never parses\n", encoding="utf-8")
    # a well-formed v5 entity -> parses, lands in the entity map
    (mem / "good-v5.md").write_text(
        "---\nschema: 5\nname: good-v5\ntype: semantic\n---\n\n## Observations\n- fine\n", encoding="utf-8")
    # a corrupt v5 entity whose schema scalar is QUOTED — parse_v5_content strips quotes and accepts it, so the
    # guard must too (else it evades detection -> silent prune = the exact data loss B3 closes)
    (mem / "broken-quoted.md").write_text(
        "---\nschema: \"5\"\nname: broken-quoted\ntype: semantic\n"
        "## Observations\n- quoted schema, missing closing fence\n", encoding="utf-8")
    # negative control 1: a plain frontmatter wiki note (schema != 5) is NOT an entity -> neither map nor malformed
    (mem / "plain-note.md").write_text(
        "---\ntitle: not an entity\ntags: [x]\n---\n\n# Note\nprose only\n", encoding="utf-8")
    # negative control 2: a non-entity note whose BODY mentions `schema: 5` (a doc ABOUT the v5 format) must NOT
    # be misread as a corrupt entity — the marker scans the frontmatter block only, never the body
    (mem / "doc-note.md").write_text(
        "---\ntype: doc\n---\n\n# The v5 format\nA v5 entity's frontmatter contains:\nschema: 5\n", encoding="utf-8")
    # regression: a corrupt v4 file stays guarded too
    (mem / "broken-v4.md").write_text(
        '<memory:entity schema="4" name="broken-v4">\n  <memory:description>unclosed', encoding="utf-8")

    out, malformed = reconcile._parse_md(mem)
    flagged = {os.path.basename(f) for f in malformed}
    assert "broken-v5.md" in flagged, "corrupt v5 entity must be guarded, not pruned (B3)"
    assert "broken-quoted.md" in flagged, "corrupt v5 with a QUOTED schema must be guarded (parser accepts it)"
    assert "broken-v4.md" in flagged, "corrupt v4 entity must stay guarded"
    assert "plain-note.md" not in flagged, "a non-entity note must NOT be flagged as corruption"
    assert "doc-note.md" not in flagged, "a note that mentions `schema: 5` in its BODY must NOT be flagged"
    assert "good-v5" in out and "plain-note" not in out and "doc-note" not in out


def test_doc_machine_sections_match_render_reference_tables():
    """The schema spec's generated block is diff-checked against the authority — the machine-checkable doc
    sections cannot drift from entity_schema.py. Hermetic: reads a checked-in doc, not the live memory/ dir."""
    import re
    import pathlib
    doc = (pathlib.Path(__file__).resolve().parent.parent / 'docs' / 'schema-specification.md').read_text(encoding='utf-8')
    m = re.search(r'<!-- BEGIN generated[^>]*-->\n(.*?)\n<!-- END generated -->', doc, re.S)
    assert m, 'generated markers missing from schema-specification.md'
    assert m.group(1).strip() == SCH.render_reference_tables().strip(), 'doc generated block drifted from entity_schema.py'
