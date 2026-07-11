"""Tests for schema validator."""

import pytest

from memoryschema.validator import (
    validate, validate_file, extract_entity_block, parse_entity,
)


# --- Valid entities ---

MINIMAL_VALID = """<memory:entity schema="2" name="test-entity">
  <memory:description>A valid test entity</memory:description>
</memory:entity>"""

FULL_VALID = """<memory:entity schema="2" name="test-full" type="semantic" importance="7">
  <memory:description>Full entity with all fields</memory:description>
  <memory:observations>
    <memory:observation>Fact one</memory:observation>
    <memory:observation>Fact two</memory:observation>
  </memory:observations>
  <memory:prompt>What was asked</memory:prompt>
  <memory:reasoning>Why this approach</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="INFORMS"/>
  </memory:relations>
  <memory:source>test-session</memory:source>
</memory:entity>"""


# --- Invalid entities ---

NO_ENTITY = "Just some markdown text with no entity."

NO_NAME = """<memory:entity schema="2">
  <memory:description>Missing name</memory:description>
</memory:entity>"""

NO_DESCRIPTION = """<memory:entity schema="2" name="no-desc">
</memory:entity>"""

EMPTY_TYPE = """<memory:entity schema="2" name="bad-type" type="">
  <memory:description>Empty type</memory:description>
</memory:entity>"""

FREEFORM_TYPE = """<memory:entity schema="2" name="custom-type" type="investigation">
  <memory:description>Custom type</memory:description>
</memory:entity>"""

INVALID_IMPORTANCE_RANGE = """<memory:entity schema="2" name="bad-imp" importance="15">
  <memory:description>Importance out of range</memory:description>
</memory:entity>"""

INVALID_IMPORTANCE_STRING = """<memory:entity schema="2" name="bad-imp-str" importance="high">
  <memory:description>Importance not integer</memory:description>
</memory:entity>"""

INVALID_SCHEMA_VERSION = """<memory:entity schema="99" name="bad-schema">
  <memory:description>Schema version too high</memory:description>
</memory:entity>"""

SELF_REFERENCE = """<memory:entity schema="2" name="self-ref">
  <memory:description>Self-referencing relation</memory:description>
  <memory:relations>
    <memory:relation target="self-ref" type="USES"/>
  </memory:relations>
</memory:entity>"""

INVALID_RELATION_TYPE = """<memory:entity schema="2" name="bad-rel">
  <memory:description>Invalid relation type</memory:description>
  <memory:relations>
    <memory:relation target="other" type="LOVES"/>
  </memory:relations>
</memory:entity>"""

DUPLICATE_RELATION = """<memory:entity schema="2" name="dup-rel">
  <memory:description>Duplicate relations</memory:description>
  <memory:relations>
    <memory:relation target="other" type="USES"/>
    <memory:relation target="other" type="USES"/>
  </memory:relations>
</memory:entity>"""

EMPTY_OBSERVATIONS = """<memory:entity schema="2" name="empty-obs">
  <memory:description>Empty observations block</memory:description>
  <memory:observations>
  </memory:observations>
</memory:entity>"""

INGESTED_NO_SOURCE = """<memory:entity schema="3" name="ingested-no-src" provenance="ingested">
  <memory:description>Ingested without source</memory:description>
</memory:entity>"""

INGESTED_WITH_SOURCE = """<memory:entity schema="3" name="ingested-with-src" provenance="ingested">
  <memory:description>Ingested with source</memory:description>
  <memory:source>https://example.com/data.json</memory:source>
</memory:entity>"""


class TestValidEntities:
    def test_minimal(self):
        errors = validate(MINIMAL_VALID)
        assert errors == []

    def test_full(self):
        errors = validate(FULL_VALID)
        assert errors == []

    def test_with_body(self):
        content = MINIMAL_VALID + "\n\nSome body text after the entity."
        errors = validate(content)
        assert errors == []


class TestStructureRules:
    def test_v1_no_entity(self):
        errors = validate(NO_ENTITY)
        assert any(r == 'V1' for r, _ in errors)

    def test_v2_no_name(self):
        errors = validate(NO_NAME)
        assert any(r == 'V2' for r, _ in errors)

    def test_v6_no_description(self):
        errors = validate(NO_DESCRIPTION)
        assert any(r == 'V6' for r, _ in errors)

    def test_v4_empty_type_rejected(self):
        errors = validate(EMPTY_TYPE)
        assert any(r == 'V4' for r, _ in errors)

    def test_v4_freeform_type_accepted(self):
        errors = validate(FREEFORM_TYPE)
        assert not any(r == 'V4' for r, _ in errors)

    def test_v5_importance_out_of_range(self):
        errors = validate(INVALID_IMPORTANCE_RANGE)
        assert any(r == 'V5' for r, _ in errors)

    def test_v5_importance_not_integer(self):
        errors = validate(INVALID_IMPORTANCE_STRING)
        assert any(r == 'V5' for r, _ in errors)

    def test_v10_schema_version(self):
        errors = validate(INVALID_SCHEMA_VERSION)
        assert any(r == 'V10' for r, _ in errors)

    def test_v10_v4_ceiling_is_four_not_current_schema_version(self):
        # B4 boundary: the v4-XML `schema=` ceiling stays 4 (V4_XML_SCHEMA_VERSION), NOT SCHEMA_VERSION (=5).
        # `schema="99"` alone can't catch a regression that reconciles the bound to 5; `schema="5"` can.
        v4_5 = '<memory:entity schema="5" name="x"><memory:description>d</memory:description></memory:entity>'
        v4_4 = '<memory:entity schema="4" name="x"><memory:description>d</memory:description></memory:entity>'
        assert any(r == 'V10' for r, _ in validate(v4_5)), "a v4 schema=5 must be out of range (ceiling is 4)"
        assert not any(r == 'V10' for r, _ in validate(v4_4)), "a v4 schema=4 must be in range"

    def test_v7_empty_observations(self):
        errors = validate(EMPTY_OBSERVATIONS)
        assert any(r == 'V7' for r, _ in errors)



class TestRelationRules:
    def test_r4_self_reference(self):
        errors = validate(SELF_REFERENCE)
        assert any(r == 'R4' for r, _ in errors)

    def test_r2_invalid_type(self):
        errors = validate(INVALID_RELATION_TYPE)
        assert any(r == 'R2' for r, _ in errors)

    def test_r5_duplicate(self):
        errors = validate(DUPLICATE_RELATION)
        assert any(r == 'R5' for r, _ in errors)


class TestFilesystemRules:
    def test_v3_filename_mismatch(self):
        errors = validate(MINIMAL_VALID, filepath="/tmp/wrong-name.md")
        assert any(r == 'V3' for r, _ in errors)

    def test_v3_filename_match(self):
        errors = validate(MINIMAL_VALID, filepath="/tmp/test-entity.md")
        assert not any(r == 'V3' for r, _ in errors)

    def test_f3_unsafe_chars(self):
        content = """<memory:entity schema="2" name="bad name">
  <memory:description>Spaces in name</memory:description>
</memory:entity>"""
        errors = validate(content, filepath="/tmp/bad name.md")
        assert any(r == 'F3' for r, _ in errors)


class TestStrictMode:
    def test_q1_not_kebab(self):
        content = """<memory:entity schema="2" name="NotKebab">
  <memory:description>Not kebab case</memory:description>
</memory:entity>"""
        errors = validate(content, strict=True)
        assert any(r == 'Q1' for r, _ in errors)

    def test_q2_long_description(self):
        long_desc = "x" * 150
        content = f"""<memory:entity schema="2" name="long-desc">
  <memory:description>{long_desc}</memory:description>
</memory:entity>"""
        errors = validate(content, strict=True)
        assert any(r == 'Q2' for r, _ in errors)


class TestExtractEntityBlock:
    def test_extract(self):
        xml, body = extract_entity_block(FULL_VALID)
        assert xml is not None
        assert '<memory:entity' in xml
        assert body is None

    def test_with_body(self):
        content = MINIMAL_VALID + "\n\nBody text here."
        xml, body = extract_entity_block(content)
        assert xml is not None
        assert body == "Body text here."

    def test_no_entity(self):
        xml, body = extract_entity_block("No entity here.")
        assert xml is None
        assert body is None


class TestParseEntity:
    def test_parse(self):
        xml, _ = extract_entity_block(MINIMAL_VALID)
        root = parse_entity(xml)
        assert root.get('name') == 'test-entity'
        assert root.find('description').text == 'A valid test entity'


class TestValidateFile:
    def test_valid_file(self, tmp_path):
        filepath = tmp_path / "test-full.md"
        filepath.write_text(FULL_VALID)
        from memoryschema.validator import validate_file
        errors = validate_file(str(filepath))
        # May have Q warnings in strict mode but no V/R/F errors
        structural = [e for e in errors if e[0].startswith(('V', 'R', 'F'))]
        assert structural == []

    def test_invalid_file(self, tmp_path):
        filepath = tmp_path / "bad.md"
        filepath.write_text(NO_DESCRIPTION)
        from memoryschema.validator import validate_file
        errors = validate_file(str(filepath))
        assert any(r == 'V6' for r, _ in errors)


class TestValidateDirectory:
    def test_mixed_directory(self, tmp_path):
        (tmp_path / "good-entity.md").write_text(MINIMAL_VALID.replace("test-entity", "good-entity"))
        (tmp_path / "bad-entity.md").write_text(NO_DESCRIPTION.replace("no-desc", "bad-entity"))
        (tmp_path / "MEMORY.md").write_text("Index — should be skipped")
        (tmp_path / "not-md.txt").write_text("Not a markdown file")

        from memoryschema.validator import validate_directory
        results = validate_directory(str(tmp_path))
        # Only bad-entity.md should have errors
        assert len(results) == 1
        bad_path = str(tmp_path / "bad-entity.md")
        assert bad_path in results

    def test_all_valid(self, tmp_path):
        (tmp_path / "entity-a.md").write_text(MINIMAL_VALID.replace("test-entity", "entity-a"))
        (tmp_path / "entity-b.md").write_text(MINIMAL_VALID.replace("test-entity", "entity-b"))
        from memoryschema.validator import validate_directory
        results = validate_directory(str(tmp_path))
        assert results == {}

    def test_empty_directory(self, tmp_path):
        from memoryschema.validator import validate_directory
        results = validate_directory(str(tmp_path))
        assert results == {}
