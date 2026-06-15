<memory:entity schema="4" name="five-space-eval-results" type="semantic" importance="7">
  <memory:description>5-space eval: nDCG 0.555, recall 0.511 — continues downward trend with equal-weight combiner</memory:description>
  <memory:observations>
    <memory:observation basis="measured">5-space nDCG@10=0.555, recall@5=0.511, MRR=0.736 — worse than single-space (0.608, 0.622, 0.778)</memory:observation>
    <memory:observation basis="measured">Monotonic degradation: single 0.608 → 3-space 0.601 → 4-space 0.557 → 5-space 0.555</memory:observation>
    <memory:observation basis="measured">Setup/deploy query worst affected: -0.270 nDCG from single-space</memory:observation>
    <memory:observation basis="inferred">The spaces have genuine discriminative value but the equal-weight combiner averages them destructively</memory:observation>
    <memory:observation basis="inferred">Next step: query-conditioned weighting — match query to most relevant space(s) instead of averaging all</memory:observation>
  </memory:observations>
  <memory:prompt>User asked to run eval with 5 spaces</memory:prompt>
  <memory:reasoning>The pattern is clear: each additional space with equal weight dilutes the strong default signal. The default space already captures the full semantic blend. Field spaces add noise when averaged equally. The infrastructure is correct — the combiner strategy is the bottleneck. Query-conditioned weighting (classify query type → weight relevant spaces higher) is the path forward.</memory:reasoning>
</memory:entity>
