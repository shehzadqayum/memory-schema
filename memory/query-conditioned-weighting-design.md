<memory:entity schema="4" name="query-conditioned-weighting-design" type="semantic" importance="9">
  <memory:description>Query-conditioned weighting design: classify query by keywords, select space weight profile per type</memory:description>
  <memory:observations>
    <memory:observation basis="measured">desc+default static profile beats single-space: recall@5=0.678 vs 0.622, nDCG=0.747 vs 0.739</memory:observation>
    <memory:observation basis="measured">Query-conditioned achieves same recall (0.678) with keyword-based classification into factual/rationale/intent/general</memory:observation>
    <memory:observation basis="measured">Key insight: description space at 2-3x weight improves factual queries (hierarchy 0.33→0.67, setup 0.33→0.67)</memory:observation>
    <memory:observation basis="inferred">Static desc+default weights are the minimum viable improvement — query-conditioned adds value only with diverse query types</memory:observation>
    <memory:observation>Four query types: factual (desc+obs heavy), rationale (reasoning heavy), intent (prompt heavy), general (desc+default fallback)</memory:observation>
    <memory:observation>Classification is zero-cost: keyword regex on query text, no API call needed</memory:observation>
  </memory:observations>
  <memory:prompt>User asked to show how query-conditioned weighting could work</memory:prompt>
  <memory:reasoning>Equal-weight averaging was the bottleneck, not the spaces. The description space has high discriminative power (proven in earlier analysis). Weighting it at 2-3x in combination with default at 2x gives the best results. Query-conditioned classification adds the ability to shift weight to reasoning or prompt spaces for non-factual queries, but the static desc+default profile is already a significant improvement.</memory:reasoning>
</memory:entity>
