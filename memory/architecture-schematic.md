<memory:entity schema="4" name="architecture-schematic" type="knowledge" importance="8" confidence="9">
  <memory:description>Full architecture schematic: entity schema, write pipeline, scoring, relations, chains, storage layers</memory:description>
  <memory:observations>
    <memory:observation>7 sections: entity schema (13+9 fields), write pipeline (hook→auth→embed→gate→store→L0), scoring (variance-weighted combiner), relations (7 types), chains (start→update→release), storage (5 layers), current state</memory:observation>
    <memory:observation>Write pipeline: PostToolUse hook → authorisation check → parse XML → embed 7 spaces → divergence profile → 4-stage gate → dual-backend store → MEMORY.md update</memory:observation>
    <memory:observation>Scoring: recency × w_r + importance × w_i + relevance × w_v, then × confidence/10 + hub bonus + BM25 + MITIGATES dampening</memory:observation>
    <memory:observation>Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — default weight 1.0, field spaces weighted by divergence</memory:observation>
    <memory:observation>96 entries, 83 active, 7 spaces, 4-stage gate, 627 tests, content-agnostic</memory:observation>
  </memory:observations>
  <memory:prompt>Provide a full schematic of the architecture</memory:prompt>
  <memory:reasoning>The schematic captures the complete system in ASCII art: entity structure with all fields and their upsert behaviors, the full write pipeline from hook trigger to L0 update, the variance-weighted scoring formula, the recall cascade, the relation graph, the chain lifecycle, and the storage layer degradation chain.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
