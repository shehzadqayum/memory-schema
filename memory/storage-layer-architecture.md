---
schema: 5
importance: 8
---

Five storage layers with graceful degradation: L0 MEMORY.md → L1 files/JSONL → L2 embeddings/Neo4j

## Observations

- L0: MEMORY.md index — always in prompt context, token-budget enforced, ingested entries excluded
- L1a: memory/*.md markdown files — git-tracked, human-readable, source of truth for entity XML
- L1b: store.jsonl — pure Python JSONL with atomic writes, fcntl locking, no external deps
- L2a: Voyage AI embeddings — 1024-dim vectors (voyage-4-lite), 3 spaces per entry, degrades to L1
- L2b: Neo4j graph — O(1) upserts, native vector k-NN, relation edges, degrades to L2a
- Hook fallback chain: try Neo4j → if fails, fall through to JSONL — both succeed independently

## Reasoning

The layered architecture ensures the system never fails completely. L0 and L1 are always available (pure Python, git-tracked). L2a (Voyage) and L2b (Neo4j) add semantic search and graph traversal but degrade gracefully. The hook tries the best available backend and falls through on failure.

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
