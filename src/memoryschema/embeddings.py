"""
Voyage AI embeddings wrapper.

Thin client for embedding text and reranking documents.
Requires: pip install memory-schema[embeddings]

Usage:
    from memoryschema import embed_text, embed_batch, rerank
    vector = embed_text("hello world")  # 1024-dim list of floats
"""

import voyageai


_cached_client = None


def get_client(api_key=None, config=None):
    """Get or create a cached Voyage AI client.

    Args:
        api_key: Optional API key. If None, uses config or VOYAGE_API_KEY env var.
        config: Optional MemoryConfig instance.

    Returns:
        voyageai.Client instance.
    """
    global _cached_client
    if _cached_client is not None and api_key is None:
        return _cached_client

    if api_key is None and config is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()
    if api_key is None and config:
        api_key = config.voyage_api_key

    client = voyageai.Client(api_key=api_key)

    if config is not None:
        _cached_client = client

    return client


def embed_text(text, client=None, config=None):
    """Embed a single text string.

    Args:
        text: Text to embed.
        client: Optional voyageai.Client.
        config: Optional MemoryConfig for model selection.

    Returns:
        List of floats (1024-dim embedding vector).
    """
    if client is None:
        client = get_client(config=config)

    model = config.embed_model if config else 'voyage-4-lite'
    result = client.embed(texts=[text], model=model)
    return result.embeddings[0]


def embed_batch(texts, client=None, config=None):
    """Embed multiple texts in a single API call.

    Args:
        texts: List of text strings to embed.
        client: Optional voyageai.Client.
        config: Optional MemoryConfig for model selection.

    Returns:
        List of embedding vectors (each 1024-dim).
    """
    if client is None:
        client = get_client(config=config)

    model = config.embed_model if config else 'voyage-4-lite'
    result = client.embed(texts=texts, model=model)
    return result.embeddings


def rerank(query, documents, limit=5, client=None, config=None):
    """Rerank documents against a query.

    Args:
        query: Search query string.
        documents: List of document strings to rerank.
        limit: Maximum number of results to return.
        client: Optional voyageai.Client.
        config: Optional MemoryConfig for model selection.

    Returns:
        List of dicts with 'document', 'score', and 'index' keys,
        ordered by relevance score descending.
    """
    if client is None:
        client = get_client(config=config)

    model = config.rerank_model if config else 'rerank-2'
    result = client.rerank(
        query=query,
        documents=documents,
        model=model,
        top_k=limit,
    )

    return [
        {
            'document': r.document,
            'score': r.relevance_score,
            'index': r.index,
        }
        for r in result.results
    ]
