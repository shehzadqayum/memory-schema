"""Tests for embeddings module — Voyage AI wrapper (mocked)."""

from unittest.mock import patch, MagicMock

import pytest

from memoryschema.config import MemoryConfig


@pytest.fixture
def mock_voyageai():
    """Mock voyageai.Client with predictable responses."""
    mock_client = MagicMock()
    mock_client.embed.return_value = MagicMock(embeddings=[[0.1] * 1024])
    mock_client.rerank.return_value = MagicMock(results=[
        MagicMock(document="doc1", relevance_score=0.95, index=0),
        MagicMock(document="doc2", relevance_score=0.80, index=1),
    ])
    with patch("memoryschema.embeddings.voyageai") as mock_module:
        mock_module.Client.return_value = mock_client
        # Reset cached client
        import memoryschema.embeddings as emb
        emb._cached_client = None
        yield mock_client, mock_module


class TestGetClient:
    def test_creates_client(self, mock_voyageai):
        mock_client, mock_module = mock_voyageai
        from memoryschema.embeddings import get_client
        client = get_client(api_key="test-key")
        mock_module.Client.assert_called_with(api_key="test-key")

    def test_caches_client(self, mock_voyageai):
        mock_client, mock_module = mock_voyageai
        from memoryschema.embeddings import get_client
        c1 = get_client()
        c2 = get_client()
        assert mock_module.Client.call_count == 1

    def test_config_api_key(self, mock_voyageai):
        mock_client, mock_module = mock_voyageai
        from memoryschema.embeddings import get_client
        config = MemoryConfig(voyage_api_key="config-key")
        import memoryschema.embeddings as emb
        emb._cached_client = None
        get_client(config=config)
        mock_module.Client.assert_called_with(api_key="config-key")


class TestEmbedText:
    def test_returns_vector(self, mock_voyageai):
        mock_client, _ = mock_voyageai
        from memoryschema.embeddings import embed_text
        result = embed_text("hello world")
        assert len(result) == 1024
        mock_client.embed.assert_called_once()

    def test_uses_config_model(self, mock_voyageai):
        mock_client, _ = mock_voyageai
        from memoryschema.embeddings import embed_text
        config = MemoryConfig(embed_model="custom-model")
        embed_text("test", config=config)
        call_args = mock_client.embed.call_args
        assert call_args.kwargs.get("model") == "custom-model" or call_args[1].get("model") == "custom-model"


class TestEmbedBatch:
    def test_returns_vectors(self, mock_voyageai):
        mock_client, _ = mock_voyageai
        mock_client.embed.return_value = MagicMock(embeddings=[[0.1] * 1024, [0.2] * 1024])
        from memoryschema.embeddings import embed_batch
        result = embed_batch(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 1024


class TestRerank:
    def test_returns_ranked_results(self, mock_voyageai):
        mock_client, _ = mock_voyageai
        from memoryschema.embeddings import rerank
        result = rerank("query", ["doc1", "doc2"], limit=2)
        assert len(result) == 2
        assert result[0]["document"] == "doc1"
        assert result[0]["score"] == 0.95
        assert result[0]["index"] == 0

    def test_uses_config_model(self, mock_voyageai):
        mock_client, _ = mock_voyageai
        from memoryschema.embeddings import rerank
        config = MemoryConfig(rerank_model="custom-rerank")
        rerank("query", ["doc"], config=config)
        call_args = mock_client.rerank.call_args
        assert "custom-rerank" in str(call_args)
