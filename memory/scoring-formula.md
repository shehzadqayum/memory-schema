<memory:entity schema="4" name="scoring-formula" type="semantic" importance="7">
  <memory:description>Retrieval scoring: recency × w_r + importance × w_i + cosine_sim × w_v with type/trust/basis modifiers</memory:description>
  <memory:observations>
    <memory:observation>Semantic mode weights: recency=0.2, importance=0.3, relevance=0.5</memory:observation>
    <memory:observation>Structured mode weights: recency=0.3, importance=0.5, relevance=0.2</memory:observation>
    <memory:observation>Recency: 0.995^hours — semantic floor 0.6, procedural access-reinforced (exponent 1/(1+0.3*accesses)), episodic standard</memory:observation>
    <memory:observation>Trust multipliers: first-party=1.0, user=1.0, derived=0.9, ingested=0.7</memory:observation>
    <memory:observation>Basis factor: measured=1.0, inferred=0.97, reported=0.93 (lowest-reliability observation determines factor)</memory:observation>
    <memory:observation>Hub bonus: 0.05 * ln(1 + backlinks) — log-scale prevents rich-get-richer</memory:observation>
    <memory:observation>BM25 text match boost: up to +0.3 for keyword overlap</memory:observation>
    <memory:observation>MITIGATES dampening: 0.95 multiplier for entries with inbound MITIGATES relations</memory:observation>
  </memory:observations>
  <memory:reasoning>The scoring formula balances recency, importance, and semantic relevance with type-specific decay curves. This ensures semantic knowledge persists, procedural patterns reinforce with use, and episodic events naturally fade. Trust and basis modifiers prevent low-quality content from outranking verified facts.</memory:reasoning>
</memory:entity>
