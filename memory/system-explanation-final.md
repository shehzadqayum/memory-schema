<memory:entity schema="4" name="system-explanation-final" type="knowledge" importance="7">
  <memory:description>Full memory system explanation: 7 spaces, variance-weighted combiner, authorised/unauthorised states, chain entities</memory:description>
  <memory:observations>
    <memory:observation>7 embedding spaces: 1:1 field-to-space mapping (name, description, observations, prompt, reasoning, chain) + default blend</memory:observation>
    <memory:observation>Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no heuristics, data determines weights</memory:observation>
    <memory:observation>Two memory states: unauthorised (read-only, default) and authorised (active chain only, one at a time)</memory:observation>
    <memory:observation>Write pipeline: authorisation check → parse → embed 7 spaces → divergence profile → gate 6 stages → store → MEMORY.md</memory:observation>
    <memory:observation>Chain entities: start (authorise) → update (upsert) → release (read-only permanent). Chain field enables grouping via vector similarity.</memory:observation>
    <memory:observation>81 entries, 69 active, 7 spaces, 79 relations, 800 associations, 681 tests</memory:observation>
  </memory:observations>
  <memory:prompt>Explain how our memory system works</memory:prompt>
  <memory:reasoning>The system is architecturally complete: every field maps to an embedding space, divergence profiles enable self-regulating weight, authorisation gates enforce immutability with a single writable chain exception, and the full pipeline runs automatically on every write via the PostToolUse hook.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
