<memory:entity schema="4" name="chain-implementing-live-chains" type="knowledge" importance="9">
  <memory:description>Chain: 7-space architecture complete — all documentation synchronized with implementation</memory:description>
  <memory:observations>
    <memory:observation>7 spaces: default + name + description + observations + prompt + reasoning + chain (7168 max dims)</memory:observation>
    <memory:observation>Chain field is free text with own embedding space — consistent 1:1 field-to-space mapping</memory:observation>
    <memory:observation>Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no base weights, no heuristics</memory:observation>
    <memory:observation>Chain divergence reveals role: high = step in investigation, low = standalone or chain entity itself</memory:observation>
    <memory:observation>All documentation synchronized: schema.md, rules, design doc, working guidelines — 670 tests passing</memory:observation>
  </memory:observations>
  <memory:prompt>Update and synchronise all documentation with current development</memory:prompt>
  <memory:reasoning>The architecture is now fully consistent and documented: every entity field maps 1:1 to an embedding space, the variance-weighted combiner handles all weighting automatically from divergence profiles computed at embed time, and the chain field enables reasoning sequence grouping through natural vector similarity.</memory:reasoning>
  <memory:chain>designing and implementing the memory system's multi-space embedding architecture</memory:chain>
  <memory:relations>
    <memory:relation target="chain-entity-design" type="USES"/>
    <memory:relation target="chain-live-accumulation-design" type="USES"/>
  </memory:relations>
</memory:entity>
