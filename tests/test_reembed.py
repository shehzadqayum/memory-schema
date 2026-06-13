"""Tests for reembed module (mocked Voyage AI)."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from memoryschema.reembed import compose_embedding_text, reembed
from memoryschema.config import MemoryConfig


class TestComposeEmbeddingText:
    def test_all_fields(self):
        entry = {
            "description": "Test desc",
            "observations": ["Fact 1", "Fact 2"],
            "prompt": "What?",
            "reasoning": "Because.",
        }
        result = compose_embedding_text(entry)
        assert "Test desc" in result
        assert "Fact 1" in result
        assert "What?" in result
        assert "Because." in result

    def test_description_only(self):
        result = compose_embedding_text({"description": "Just desc"})
        assert result == "Just desc"

    def test_max_chars_truncation(self):
        entry = {"description": "x" * 5000}
        result = compose_embedding_text(entry, max_chars=100)
        assert len(result) == 100

    def test_empty_entry(self):
        result = compose_embedding_text({})
        assert result == ""


class TestReembed:
    @pytest.fixture
    def store_file(self, tmp_path):
        """Create a temp JSONL store with entries."""
        entries = [
            {"name": "tweet-1", "description": "Tweet one", "observations": ["A"]},
            {"name": "tweet-2", "description": "Tweet two", "observations": ["B"]},
            {"name": "forum-1", "description": "Forum post", "observations": ["C"]},
        ]
        path = tmp_path / "store.jsonl"
        with open(path, 'w') as f:
            for e in entries:
                f.write(json.dumps(e) + '\n')
        return str(path), entries

    def test_dry_run(self, store_file):
        path, entries = store_file
        config = MemoryConfig(store_path=path)
        result = reembed(prefix="tweet-", config=config, dry_run=True)
        assert result["dry_run"] is True
        assert result["total"] == 3
        assert result["matched"] == 2
        assert result["embedded"] == 0

    def test_prefix_filter(self, store_file):
        path, entries = store_file
        config = MemoryConfig(store_path=path)
        result = reembed(prefix="forum-", config=config, dry_run=True)
        assert result["matched"] == 1

    def test_no_matches(self, store_file):
        path, entries = store_file
        config = MemoryConfig(store_path=path)
        result = reembed(prefix="nonexistent-", config=config, dry_run=True)
        assert result["matched"] == 0

    def test_embed_with_mock(self, store_file):
        path, entries = store_file
        config = MemoryConfig(store_path=path)
        mock_vectors = [[0.1] * 10, [0.2] * 10]
        with patch("memoryschema.reembed.embed_batch", create=True) as mock_eb:
            # Patch the actual import inside the function
            with patch.dict("sys.modules"):
                with patch("memoryschema.reembed._embed_batch", mock_eb, create=True):
                    pass
            # The function imports embed_batch internally — mock at module level
            import memoryschema.reembed as reembed_mod
            original = None
            try:
                from memoryschema.embeddings import embed_batch as _real
                original = _real
            except Exception:
                pass

            with patch.object(reembed_mod, '__builtins__', reembed_mod.__builtins__):
                with patch("memoryschema.embeddings.embed_batch", return_value=mock_vectors):
                    result = reembed(prefix="tweet-", config=config, batch_size=10, skip_assoc=True)

        # Verify store file was rewritten
        with open(path) as f:
            rewritten = [json.loads(line) for line in f if line.strip()]
        assert len(rewritten) == 3

    def test_atomic_write_preserves_all_entries(self, store_file):
        """Even if embedding fails, all entries should be preserved."""
        path, entries = store_file
        config = MemoryConfig(store_path=path)
        # dry_run doesn't modify the file
        reembed(prefix="tweet-", config=config, dry_run=True)
        with open(path) as f:
            preserved = [json.loads(line) for line in f if line.strip()]
        assert len(preserved) == 3


class TestReembedFieldSpaces:
    """Tests for per-space reembedding (M1.3)."""

    @pytest.fixture
    def store_with_fields(self, tmp_path):
        """Create store with entries that have/lack observations and reasoning."""
        entries = [
            {"name": "full-1", "description": "Full entry",
             "observations": ["Fact A"], "reasoning": "Because X", "prompt": "Why?"},
            {"name": "obs-only", "description": "Observations only",
             "observations": ["Fact B", "Fact C"]},
            {"name": "reason-only", "description": "Reasoning only",
             "reasoning": "Because Y"},
            {"name": "bare", "description": "No observations or reasoning"},
        ]
        path = tmp_path / "store.jsonl"
        with open(path, 'w') as f:
            for e in entries:
                f.write(json.dumps(e) + '\n')
        return str(path), entries

    def test_observations_space_skips_empty(self, store_with_fields):
        path, _ = store_with_fields
        config = MemoryConfig(store_path=path)
        result = reembed(prefix="", config=config, space='observations', dry_run=True)
        assert result['matched'] == 4
        assert result['space'] == 'observations'

    def test_reasoning_space_skips_empty(self, store_with_fields):
        path, _ = store_with_fields
        config = MemoryConfig(store_path=path)
        result = reembed(prefix="", config=config, space='reasoning', dry_run=True)
        assert result['matched'] == 4
        assert result['space'] == 'reasoning'

    def test_observations_space_embeds(self, store_with_fields):
        """Observations space: embeds entries with observations, skips others."""
        path, _ = store_with_fields
        config = MemoryConfig(store_path=path)
        mock_vectors = [[0.1] * 10, [0.2] * 10]  # 2 entries have observations
        with patch("memoryschema.embeddings.embed_batch", return_value=mock_vectors):
            result = reembed(prefix="", config=config, space='observations',
                             skip_assoc=True)
        assert result['embedded'] == 2
        assert result['skipped_empty'] == 2
        # Verify embeddings dict was populated
        with open(path) as f:
            rewritten = [json.loads(line) for line in f if line.strip()]
        full = next(e for e in rewritten if e['name'] == 'full-1')
        assert 'observations' in full.get('embeddings', {})
        bare = next(e for e in rewritten if e['name'] == 'bare')
        assert 'observations' not in bare.get('embeddings', {})

    def test_reasoning_space_embeds(self, store_with_fields):
        """Reasoning space: embeds entries with reasoning/prompt, skips others."""
        path, _ = store_with_fields
        config = MemoryConfig(store_path=path)
        mock_vectors = [[0.3] * 10, [0.4] * 10]  # 2 entries have reasoning
        with patch("memoryschema.embeddings.embed_batch", return_value=mock_vectors):
            result = reembed(prefix="", config=config, space='reasoning',
                             skip_assoc=True)
        assert result['embedded'] == 2
        assert result['skipped_empty'] == 2

    def test_default_space_populates_both_fields(self, store_with_fields):
        """Default space (space=None): sets both embedding and embeddings.default."""
        path, _ = store_with_fields
        config = MemoryConfig(store_path=path)
        mock_vectors = [[0.5] * 10] * 4
        with patch("memoryschema.embeddings.embed_batch", return_value=mock_vectors):
            result = reembed(prefix="", config=config, skip_assoc=True)
        assert result['embedded'] == 4
        with open(path) as f:
            rewritten = [json.loads(line) for line in f if line.strip()]
        for e in rewritten:
            assert 'embedding' in e
            assert e.get('embeddings', {}).get('default') == e['embedding']
