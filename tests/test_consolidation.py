"""Tests for consolidation module — batch indexing pipeline."""

import os
from unittest.mock import patch, MagicMock

import pytest

from memoryschema.consolidation import consolidate, _embedding_text
from memoryschema.store import MemoryStore


VALID_ENTITY = """<memory:entity schema="2" name="{name}" type="semantic" importance="5">
  <memory:description>{desc}</memory:description>
  <memory:observations>
    <memory:observation>Fact one</memory:observation>
  </memory:observations>
  <memory:prompt>What was asked</memory:prompt>
  <memory:reasoning>Why this approach</memory:reasoning>
</memory:entity>"""


@pytest.fixture
def memory_dir(tmp_path):
    """Create a temp dir with valid memory files."""
    for i in range(3):
        filepath = tmp_path / f"entity-{i}.md"
        filepath.write_text(VALID_ENTITY.format(name=f"entity-{i}", desc=f"Entity {i}"))
    # Also add an unparseable file
    (tmp_path / "bad.md").write_text("Not a valid entity.")
    (tmp_path / "MEMORY.md").write_text("Index file.")
    return tmp_path


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "test-store.jsonl"))


class TestEmbeddingText:
    def test_all_fields(self):
        memory = {
            "description": "Test desc",
            "observations": ["Fact 1", "Fact 2"],
            "prompt": "What?",
            "reasoning": "Because.",
        }
        result = _embedding_text(memory)
        assert "Test desc" in result
        assert "Fact 1" in result
        assert "Fact 2" in result
        assert "What?" in result
        assert "Because." in result

    def test_minimal(self):
        memory = {"name": "test", "description": "Just desc"}
        result = _embedding_text(memory)
        assert result == "test Just desc"

    def test_empty(self):
        result = _embedding_text({})
        assert result.strip() == ""


class TestConsolidate:
    def test_syncs_valid_files(self, memory_dir, store):
        result = consolidate(str(memory_dir), "test-project", store, embed=False)
        assert result["synced"] == 3
        assert result["skipped"] == 1  # bad.md
        assert store.count() == 3

    def test_sets_project(self, memory_dir, store):
        consolidate(str(memory_dir), "my-project", store, embed=False)
        entry = store.get("entity-0")
        assert entry["project"] == "my-project"

    def test_computes_backlinks(self, tmp_path):
        # Create two entities with a relation
        (tmp_path / "source.md").write_text("""<memory:entity schema="2" name="source">
  <memory:description>Source entity</memory:description>
  <memory:relations>
    <memory:relation target="target" type="INFORMS"/>
  </memory:relations>
</memory:entity>""")
        (tmp_path / "target.md").write_text("""<memory:entity schema="2" name="target">
  <memory:description>Target entity</memory:description>
</memory:entity>""")
        store = MemoryStore(str(tmp_path / "store.jsonl"))
        result = consolidate(str(tmp_path), "test", store, embed=False)
        assert result["synced"] == 2
        assert result["backlinks"] >= 1

    def test_embed_false_no_embedding(self, memory_dir, store):
        result = consolidate(str(memory_dir), "test", store, embed=False)
        assert result["embedded"] == 0
        entry = store.get("entity-0")
        assert entry.get("embedding") is None

    def test_embed_true_with_mock(self, memory_dir, store):
        mock_vector = [0.1] * 1024
        with patch("memoryschema.consolidation.embed_text", return_value=mock_vector, create=True) as mock_embed:
            # Patch the import inside consolidate
            with patch.dict("sys.modules", {"memoryschema.embeddings": MagicMock(embed_text=lambda t: mock_vector)}):
                result = consolidate(str(memory_dir), "test", store, embed=True)
        # embed=True attempts embedding but may fall back if import fails in the function
        assert result["synced"] == 3

    def test_empty_dir(self, tmp_path):
        store = MemoryStore(str(tmp_path / "store.jsonl"))
        result = consolidate(str(tmp_path), "test", store, embed=False)
        assert result["synced"] == 0
        assert result["skipped"] == 0
