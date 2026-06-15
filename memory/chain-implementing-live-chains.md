<memory:entity schema="4" name="chain-implementing-live-chains" type="knowledge" importance="9">
  <memory:description>Chain: complete memory system demonstrated — 7 spaces, variance-weighted combiner, bidirectional traversal</memory:description>
  <memory:observations>
    <memory:observation>Demonstrated on this entity: 7 fields, 10 USES relations, 7 embedding spaces (7168 dims), divergence profile</memory:observation>
    <memory:observation basis="measured">Divergence profile: prompt 0.60, chain 0.46, name 0.39, reasoning 0.37, description 0.27, observations 0.02</memory:observation>
    <memory:observation basis="measured">Variance-weighted scoring: "facts observed" query → prompt space activated (sim 0.725 × div 0.60) → score 0.477 vs equal 0.457</memory:observation>
    <memory:observation basis="measured">Recall cascade: name lookup at depth=1 → 10 evidence memories via USES relations (scores 0.64-0.71)</memory:observation>
    <memory:observation basis="measured">Reverse traversal: four-space-eval-results → 2 chain backlinks → this chain + chain-why-equal-weight-fails</memory:observation>
    <memory:observation>141 observations accumulated through live chain upsert pattern across the session</memory:observation>
    <memory:observation>Conclusion: full system working end-to-end — write, embed, gate, store, recall, cascade, reverse traverse</memory:observation>
  </memory:observations>
  <memory:prompt>Demonstrate this memory</memory:prompt>
  <memory:reasoning>The demonstration showed every component working on a single entity: XML parsing, 7-space embedding with divergence profiles, variance-weighted scoring that amplifies distinctive fields, recall cascade through USES relations, and reverse traversal from evidence back to chain via backlinks. The system is self-regulating through computed divergence — no configuration needed.</memory:reasoning>
  <memory:chain>designing and implementing the memory system's multi-space embedding architecture</memory:chain>
  <memory:relations>
    <memory:relation target="chain-entity-design" type="USES"/>
    <memory:relation target="chain-live-accumulation-design" type="USES"/>
    <memory:relation target="storage-layer-architecture" type="USES"/>
    <memory:relation target="scoring-formula" type="USES"/>
    <memory:relation target="gate-pipeline-stages" type="USES"/>
  </memory:relations>
</memory:entity>
