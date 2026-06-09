# Example Ingest Scripts

Reference implementations for batch corpus ingestion using the `memoryschema` package.

These scripts are **examples, not core package functionality**. Copy and adapt them for your own data sources.

## Scripts

### `ingest_tweets.py`

Ingests a Twitter archive (YAML frontmatter markdown files) into the memory system.

```bash
python ingest_tweets.py \
  --archive-root /path/to/twitter/archive \
  --memory-dir /path/to/memory/tweets \
  --store-path /path/to/memory/store.jsonl \
  --project my-project \
  --embed
```

### `ingest_forum.py`

Ingests a web forum archive (SiteSucker HTML files) into the memory system.

```bash
python ingest_forum.py \
  --forum-root /path/to/forum/posts \
  --memory-dir /path/to/memory/forum \
  --store-path /path/to/memory/store.jsonl \
  --project my-project \
  --embed
```

### `consolidate_working.py`

Merges iterative working memory files into consolidated clusters.

```bash
python consolidate_working.py \
  --memory-dir /path/to/memory \
  --clusters clusters.json
```

## Writing Your Own Ingest Script

1. Read source files (any format)
2. Convert each to a memory dict:
   ```python
   memory = {
       'name': 'source-123',
       'schema': 2,
       'type': 'semantic',
       'importance': 5,
       'description': 'One-line summary',
       'observations': ['Source text paragraph 1', 'Source text paragraph 2'],
       'project': 'my-project',
   }
   ```
3. Embed in batches:
   ```python
   from memoryschema.embeddings import embed_batch
   texts = [compose_text(m) for m in batch]
   vectors = embed_batch(texts)
   for m, v in zip(batch, vectors):
       m['embedding'] = v
   ```
4. Write `.md` files and upsert to store:
   ```python
   from memoryschema.store import get_store
   store = get_store(config=config)
   store.upsert(memory)
   ```
5. Compute associations:
   ```python
   store.compute_associations(k=10)
   ```
