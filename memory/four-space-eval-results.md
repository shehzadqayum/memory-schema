<memory:entity schema="4" name="four-space-eval-results" type="semantic" importance="8">
  <memory:description>4-space eval: nDCG 0.557 worse than single-space 0.608 — equal-weight averaging dilutes signal</memory:description>
  <memory:observations>
    <memory:observation basis="measured">4-space nDCG@10=0.557, recall@5=0.567 — worse than single-space (0.608, 0.622) and 3-space (0.601, 0.622)</memory:observation>
    <memory:observation basis="measured">Setup/deploy query regressed -0.255 nDCG — field vectors pulled combined score away from strong default match</memory:observation>
    <memory:observation basis="measured">More spaces = more dilution with equal-weight combiner — each additional space averages down the default signal</memory:observation>
    <memory:observation basis="inferred">The spaces have genuine discriminative power (proven by divergence analysis) but the combiner doesn't know when to weight which space</memory:observation>
    <memory:observation basis="inferred">Fix requires query-conditioned weighting: match query type to space emphasis, not equal averaging</memory:observation>
  </memory:observations>
  <memory:prompt>User asked to evaluate if 4 spaces beats 3</memory:prompt>
  <memory:reasoning>Each additional space with equal weighting dilutes the default space signal. The default space already captures all fields blended — it's the strongest single signal. Field spaces add value only if the combiner can weight them appropriately per query. Equal averaging is the wrong combiner for multi-space retrieval.</memory:reasoning>
</memory:entity>
