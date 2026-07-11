# Corpus Memory Guidelines (importance: 4-7)

> **Unused in Helios** — no corpus scope is deployed here. Retained as the reference for
> batch source-content ingestion. Normative schema:
> `packages/memory-schema/docs/schema-specification.md`.

**Enforcement: batch — imported via scripts, no per-response requirement.** Validated at
import time. Absence from a response is not a violation.

## What to capture

Source content — documents, posts, tweets, articles. The entity is a container for
someone else's words. No reasoning is involved: observations hold the source text (one
per discrete fact or paragraph); no prompt (there was no prompt); no reasoning (nothing
was decided).

## Importance

Computed from signals in the source material: author authority (primary author 8-10,
community 3-6), engagement metrics (log-scaled), thread position (originals above
replies).

## Type

All corpus memory is `semantic` — facts and content that persist indefinitely.

## Ingestion

Write an ingest script that reads the source files, builds one entity dict per item
(current format is schema v5, authored via `write_index.create_entity_file` — v5 is the
default; no env flag needed), embeds in batches, upserts to the store, and computes
associations. See the package's `examples/` directory for reference implementations.

## File path

Write corpus entities to `memory/<corpus-name>/<prefix>-<id>.md`
(e.g. `memory/tweets/tweet-123.md`).
