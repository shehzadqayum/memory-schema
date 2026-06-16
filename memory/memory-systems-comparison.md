<memory:entity schema="4" name="memory-systems-comparison" type="knowledge" importance="7" confidence="7">
  <memory:description>How this system compares: standard RAG core + novel multi-space/variance/chains/immutability on top</memory:description>
  <memory:observations>
    <memory:observation>Standard: vector embedding, cosine similarity, recency+importance scoring — everyone does this</memory:observation>
    <memory:observation>Novel: 7 independent spaces per entry (most use 1), variance-weighted combiner (most use fixed/equal), divergence profiles as structural fingerprints</memory:observation>
    <memory:observation>Novel: chain entities with ordered reasoning + USES relations + bidirectional traversal — closer to knowledge graph than flat RAG</memory:observation>
    <memory:observation>Novel: authorised/unauthorised immutability, content-agnostic trust (confidence metadata-only)</memory:observation>
    <memory:observation>Missing vs production: no auto-chunking, no reranker in hot path, no context window budget for injection, behavioral enforcement only</memory:observation>
    <memory:observation>Fundamental pattern is still RAG: store externally, retrieve at query time, inject into context</memory:observation>
  </memory:observations>
  <memory:prompt>Is this how memory systems work?</memory:prompt>
  <memory:reasoning>The core is standard RAG. The differentiation is in the multi-space architecture (7 spaces with variance weighting), the graph structure (typed relations with cascade), and the operational model (immutability, chains, content-agnostic). These are engineering choices on top of the RAG pattern, not a fundamentally different approach. The alternative (fine-tuning) isn't practical for real-time memory.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
