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
@pytest.mark.xfail(reason="B4: SCHEMA_VERSION is still the legacy v4 marker; reconcile it to the current format",
                   strict=True)
def test_b4_schema_version_reflects_current_format():
    assert SCH.SCHEMA_VERSION == SCH.CURRENT_ENTITY_FORMAT


@pytest.mark.skip(reason="B1 (tracked): validator is v4-only — v5 entities bypass V/R/Q. Real test lands with the fix.")
def test_b1_v5_entities_are_validated():
    ...


@pytest.mark.skip(reason="B2 (tracked): create_entity_file defaults to v4 XML unless MEMORYSCHEMA_V5=1. Flip the default.")
def test_b2_new_entities_default_to_v5():
    ...


@pytest.mark.skip(reason="B3 (tracked): reconcile's malformed guard is v4-only — a corrupt v5 file is pruned (data loss).")
def test_b3_malformed_v5_is_guarded_not_pruned():
    ...


def test_doc_machine_sections_match_render_reference_tables():
    """The schema spec's generated block is diff-checked against the authority — the machine-checkable doc
    sections cannot drift from entity_schema.py. Hermetic: reads a checked-in doc, not the live memory/ dir."""
    import re
    import pathlib
    doc = (pathlib.Path(__file__).resolve().parent.parent / 'docs' / 'schema-specification.md').read_text(encoding='utf-8')
    m = re.search(r'<!-- BEGIN generated[^>]*-->\n(.*?)\n<!-- END generated -->', doc, re.S)
    assert m, 'generated markers missing from schema-specification.md'
    assert m.group(1).strip() == SCH.render_reference_tables().strip(), 'doc generated block drifted from entity_schema.py'
