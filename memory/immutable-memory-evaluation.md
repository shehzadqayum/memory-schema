<memory:entity schema="4" name="immutable-memory-evaluation" type="knowledge" importance="9">
  <memory:description>Evaluation: memories should be immutable after write — no upsert, no append, each memory a snapshot</memory:description>
  <memory:observations>
    <memory:observation>Current upsert-append model lets observations pile up (141 in one entity) and descriptions get overwritten</memory:observation>
    <memory:observation>Immutable model: every response writes a NEW memory, chain entity written ONCE at release</memory:observation>
    <memory:observation>SUPERSEDES relation replaces old memories instead of mutation</memory:observation>
    <memory:observation>Chain lifecycle changes: standalone step memories during investigation, one chain entity at release, all immutable</memory:observation>
    <memory:observation>Simplifies everything: no merge conflicts, no observation bloat, no overwritten descriptions</memory:observation>
    <memory:observation>Divergence profile computed once at write time — never needs recomputation</memory:observation>
  </memory:observations>
  <memory:prompt>Any memory should remain read-only. Evaluate.</memory:prompt>
  <memory:reasoning>The upsert model was designed for incremental enrichment but in practice caused unbounded growth and incoherent entities. Immutable memories are simpler: each is a point-in-time snapshot with a fixed embedding and divergence profile. SUPERSEDES handles evolution — the new memory replaces the old rather than mutating it. The 7-space architecture and variance-weighted combiner work identically on immutable memories.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
