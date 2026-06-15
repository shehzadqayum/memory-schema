# Corpus Memory Guidelines (importance: 4-7)

**Enforcement: batch — imported via scripts, no per-response requirement.** Validated at import time. Absence from a response is not a violation.

---

## What to capture

Source content — documents, posts, tweets, articles. The entity is a container for someone else's words. No reasoning is involved.

- `<memory:observation>` — holds the source text (one observation per discrete fact or paragraph)
- No `<memory:prompt>` (there was no prompt — the content already existed)
- No `<memory:reasoning>` (there was no decision — the content was imported as-is)

## Importance

Computed from signals in the source material:
- Author authority (e.g., primary author = 8-10, community = 3-6)
- Engagement metrics (scaled logarithmically)
- Thread position (original posts higher than replies)

## Type

All corpus memory is `semantic` — facts and content that persist indefinitely.

## Ingestion

Write an ingest script that:
1. Reads source files (any format)
2. Converts each to a `<memory:entity>` with observations holding the content
3. Embeds in batches via Voyage AI
4. Writes `.md` files to `memory/<subdir>/`
5. Bulk-writes to store (Neo4j or JSONL)
6. Computes associations

See the `examples/` directory in the memory-schema package for reference implementations.

## File path

Write corpus entities to `memory/<corpus-name>/<prefix>-<id>.md` (e.g., `memory/tweets/tweet-123.md`).
