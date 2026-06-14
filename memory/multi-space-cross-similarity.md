<memory:entity schema="4" name="multi-space-cross-similarity" type="semantic" importance="6">
  <memory:description>Cross-space embedding similarity: observations↔reasoning diverge most at ~0.66</memory:description>
  <memory:observations>
    <memory:observation basis="measured">default↔observations cosine similarity: ~0.80</memory:observation>
    <memory:observation basis="measured">default↔reasoning cosine similarity: ~0.87</memory:observation>
    <memory:observation basis="measured">observations↔reasoning cosine similarity: ~0.66 (most divergent pair)</memory:observation>
    <memory:observation basis="measured">Equal-weight combiner averages all present spaces — absent spaces are not counted as zero</memory:observation>
  </memory:observations>
  <memory:reasoning>The field spaces capture genuinely different semantic content. Observations are atomic facts, reasoning is narrative rationale. Their lower cross-similarity (0.66) confirms the spaces aren't redundant. However, the M1 gating experiment showed this divergence doesn't improve retrieval ranking with equal weights.</memory:reasoning>
</memory:entity>
