<memory:entity schema="4" name="system-description-final" type="knowledge" importance="8" confidence="9">
  <memory:description>Complete memory system: 13 LLM fields, 9 system fields, 7 spaces, 4-stage gate, content-agnostic</memory:description>
  <memory:observations>
    <memory:observation>3 required fields (schema, name, description) + 10 optional LLM fields + 9 system-managed fields</memory:observation>
    <memory:observation>7 embedding spaces: 1:1 field mapping (name, description, observations, prompt, reasoning, chain) + default blend</memory:observation>
    <memory:observation>Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no heuristics</memory:observation>
    <memory:observation>4-stage gate: validation, consistency, numeric probe, L0 echo</memory:observation>
    <memory:observation>Scoring: recency × w_r + importance × w_i + relevance × w_v, then × confidence/10</memory:observation>
    <memory:observation>Authorised/unauthorised states: only active chain writable</memory:observation>
    <memory:observation>Content-agnostic: no trust labels, no provenance, no basis — author declares importance and confidence</memory:observation>
    <memory:observation>95 entries, 83 active, 627 tests</memory:observation>
  </memory:observations>
  <memory:prompt>Describe the current memory system including all its fields</memory:prompt>
  <memory:reasoning>The system is architecturally complete and content-agnostic. Every entity field maps to an embedding space. The variance-weighted combiner handles scoring automatically from precomputed divergence profiles. Confidence replaces all trust mechanisms as a simple author-declared value.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
