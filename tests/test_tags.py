"""Tests for memory tag parser."""

import pytest

from memoryschema.tags import parse_memory_content, parse_memory_file


MINIMAL_V2 = """<memory:entity schema="2" name="test-minimal">
  <memory:description>Minimal entity</memory:description>
</memory:entity>"""

FULL_V2 = """<memory:entity schema="2" name="test-full" type="episodic" importance="8">
  <memory:description>Full v2 entity</memory:description>
  <memory:observations>
    <memory:observation>First fact</memory:observation>
    <memory:observation>Second fact</memory:observation>
  </memory:observations>
  <memory:prompt>What was the question?</memory:prompt>
  <memory:reasoning>This is the reasoning narrative.</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-entity" type="INFORMS"/>
    <memory:relation target="another" type="USES"/>
  </memory:relations>
  <memory:source>test-session-123</memory:source>
  <memory:project>test-project</memory:project>
</memory:entity>

Body text after the entity.
"""

V1_ENTITY = """<memory:entity name="v1-entity" type="semantic" importance="5">
  <memory:description>A v1 entity without schema attribute</memory:description>
  <memory:observations>
    <memory:observation>Observation one</memory:observation>
  </memory:observations>
</memory:entity>"""


class TestParseMemoryContent:
    def test_minimal(self):
        result = parse_memory_content(MINIMAL_V2)
        assert result is not None
        assert result['name'] == 'test-minimal'
        assert result['description'] == 'Minimal entity'
        assert result['schema'] == 2
        assert result['type'] == 'semantic'  # defaults to semantic when omitted
        assert result['importance'] is None
        assert result['observations'] == []
        assert result['prompt'] is None
        assert result['reasoning'] is None
        assert result['relations'] == []
        assert result['body'] is None

    def test_full_v2(self):
        result = parse_memory_content(FULL_V2)
        assert result is not None
        assert result['name'] == 'test-full'
        assert result['description'] == 'Full v2 entity'
        assert result['schema'] == 2
        assert result['type'] == 'episodic'
        assert result['importance'] == 8
        assert len(result['observations']) == 2
        assert result['observations'][0] == 'First fact'
        assert result['observations'][1] == 'Second fact'
        assert result['prompt'] == 'What was the question?'
        assert result['reasoning'] == 'This is the reasoning narrative.'
        assert len(result['relations']) == 2
        assert result['relations'][0] == {'target': 'other-entity', 'type': 'INFORMS'}
        assert result['relations'][1] == {'target': 'another', 'type': 'USES'}
        assert result['source'] == 'test-session-123'
        assert result['project'] == 'test-project'
        assert result['body'] == 'Body text after the entity.'
        assert result['related'] == ['other-entity', 'another']

    def test_v1_compatibility(self):
        result = parse_memory_content(V1_ENTITY)
        assert result is not None
        assert result['name'] == 'v1-entity'
        assert result['schema'] == 1  # default when missing
        assert result['type'] == 'semantic'
        assert result['importance'] == 5
        assert len(result['observations']) == 1

    def test_invalid_content(self):
        result = parse_memory_content("Not a memory entity at all.")
        assert result is None

    def test_empty_name(self):
        content = """<memory:entity schema="2">
  <memory:description>No name</memory:description>
</memory:entity>"""
        result = parse_memory_content(content)
        assert result is None

    def test_malformed_xml(self):
        content = """<memory:entity schema="2" name="broken">
  <memory:description>Unclosed"""
        result = parse_memory_content(content)
        assert result is None

    def test_filepath_project_derivation(self):
        result = parse_memory_content(MINIMAL_V2, filepath="/home/user/memory/projects/skills/test.md")
        assert result['project'] == 'skills'

    def test_project_element_overrides_path(self):
        result = parse_memory_content(FULL_V2, filepath="/home/user/memory/projects/other/test.md")
        assert result['project'] == 'test-project'  # from XML, not path


class TestParseMemoryFile:
    def test_nonexistent_file(self):
        result = parse_memory_file("/nonexistent/path.md")
        assert result is None

    def test_real_file(self, tmp_path):
        filepath = tmp_path / "test-entity.md"
        filepath.write_text(FULL_V2)
        result = parse_memory_file(str(filepath))
        assert result is not None
        assert result['name'] == 'test-full'
        assert result['filepath'] == str(filepath)
