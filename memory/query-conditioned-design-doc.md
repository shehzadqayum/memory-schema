<memory:entity schema="4" name="query-conditioned-design-doc" type="semantic" importance="8">
  <memory:description>Full design document written for query-conditioned weighting at docs/design/query-conditioned-weighting.md</memory:description>
  <memory:observations>
    <memory:observation>Document covers: current system architecture, 5-space embedding, scoring formula, the equal-weight dilution problem</memory:observation>
    <memory:observation>4 query types defined: factual (desc+obs heavy), rationale (reasoning heavy), intent (prompt heavy), general (desc+default fallback)</memory:observation>
    <memory:observation basis="measured">desc+default static profile: recall@5=0.678, nDCG=0.747 — beats single-space 0.622/0.739</memory:observation>
    <memory:observation>Keyword classification is zero-cost (regex on query text, no API call)</memory:observation>
    <memory:observation>Key constraint: general fallback profile must never perform worse than proven desc+default static weights</memory:observation>
  </memory:observations>
  <memory:prompt>User requested full description of current memory system and design requirements for query-conditioned weighting with examples</memory:prompt>
  <memory:reasoning>The design doc serves as the specification for implementing query-conditioned weighting. It captures the empirical findings (equal-weight worse, desc+default better), the classification approach (keyword heuristics), and the worked examples showing how different weight profiles correctly emphasize different spaces per query type.</memory:reasoning>
</memory:entity>
