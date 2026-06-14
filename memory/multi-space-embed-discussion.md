<memory:entity schema="4" name="multi-space-embed-discussion" type="semantic" importance="5">
  <memory:description>Discussion about enabling per-write multi-space embedding using M1 infrastructure</memory:description>
  <memory:observations>
    <memory:observation>M1 infrastructure is fully built: compose_embedding_text for 3 spaces, embeddings dict storage, multi-space scoring, coverage-aware combiner</memory:observation>
    <memory:observation>M1 experiment showed multi-space scoring didn't beat single-space (nDCG 0.601 vs 0.608), but vectors can serve other purposes</memory:observation>
    <memory:observation>Trade-off: 3 Voyage API calls per write (~4.8s) instead of 1 (~1.6s)</memory:observation>
  </memory:observations>
  <memory:prompt>User asked if we can use the multi-space feature per embedding</memory:prompt>
  <memory:reasoning>The infrastructure exists but isn't wired into the hook. Enabling it means modifying the hook's embed block to call compose_embedding_text for each space and store vectors in the embeddings dict.</memory:reasoning>
</memory:entity>
