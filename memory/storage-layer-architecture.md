<memory:entity schema="4" name="storage-layer-architecture" type="semantic" importance="8">
  <memory:description>Five storage layers with graceful degradation: L0 MEMORY.md → L1 files/JSONL → L2 embeddings/Neo4j</memory:description>
  <memory:observations>
    <memory:observation>L0: MEMORY.md index — always in prompt context, token-budget enforced, ingested entries excluded</memory:observation>
    <memory:observation>L1a: memory/*.md markdown files — git-tracked, human-readable, source of truth for entity XML</memory:observation>
    <memory:observation>L1b: store.jsonl — pure Python JSONL with atomic writes, fcntl locking, no external deps</memory:observation>
    <memory:observation>L2a: Voyage AI embeddings — 1024-dim vectors (voyage-4-lite), 3 spaces per entry, degrades to L1</memory:observation>
    <memory:observation>L2b: Neo4j graph — O(1) upserts, native vector k-NN, relation edges, degrades to L2a</memory:observation>
    <memory:observation>Hook fallback chain: try Neo4j → if fails, fall through to JSONL — both succeed independently</memory:observation>
  </memory:observations>
  <memory:reasoning>The layered architecture ensures the system never fails completely. L0 and L1 are always available (pure Python, git-tracked). L2a (Voyage) and L2b (Neo4j) add semantic search and graph traversal but degrade gracefully. The hook tries the best available backend and falls through on failure.</memory:reasoning>
</memory:entity>
