<memory:entity schema="4" name="complete-schematic" type="knowledge" importance="8" confidence="9">
  <memory:description>Complete system schematic: entity, write pipeline, retrieval, relations, chains, storage, field mapping</memory:description>
  <memory:observations>
    <memory:observation>8 sections: entity (13+9 fields), write pipeline (hook→auth→embed→gate→store→L0), retrieval (scoring+combiner+cascade), relations (7 types), chains (lifecycle), storage (5 layers), field-to-space mapping (1:1), current state</memory:observation>
    <memory:observation>Write pipeline: PostToolUse → parse → auth check → 7-space embed → divergence profile → 4-stage gate → dual store → MEMORY.md</memory:observation>
    <memory:observation>Retrieval: recency × importance × relevance + bonuses, variance-weighted combiner Σ(sim×div)/Σ(div), cascade through relations/backlinks/associations</memory:observation>
    <memory:observation>105 entries, 92 active, 7 spaces, 1030 associations, 627 tests, content-agnostic</memory:observation>
  </memory:observations>
  <memory:prompt>Show how the memory system works with schematics and pipelines</memory:prompt>
  <memory:reasoning>The schematic captures every component of the system in ASCII art: from the entity XML structure through the full write pipeline (hook, auth, embed, gate, store, L0), the retrieval formula (scoring, variance-weighted combiner, recall cascade), the relation graph, chain lifecycle, storage layer degradation, and the 1:1 field-to-space mapping matrix.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
