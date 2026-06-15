<memory:entity schema="4" name="system-explanation-post-provenance" type="knowledge" importance="8">
  <memory:description>Complete memory system after provenance removal: 13 LLM fields, 7 spaces, 4-stage gate, basis-based trust</memory:description>
  <memory:observations>
    <memory:observation>13 LLM-authored fields: schema, name, description (required) + type, importance, observations, prompt, reasoning, chain, relations, source, project, body</memory:observation>
    <memory:observation>10 system-managed fields: status, embedding, embeddings, divergence_profile, created_at, last_accessed, access_count, verified_at, backlinks, associations</memory:observation>
    <memory:observation>7 embedding spaces: default + name + description + observations + prompt + reasoning + chain (7168 max dims)</memory:observation>
    <memory:observation>4-stage gate: validation, consistency, numeric probe, L0 echo (provenance stages removed)</memory:observation>
    <memory:observation>Trust via basis attribute on observations (measured/inferred/reported) — per-observation, epistemological</memory:observation>
    <memory:observation>Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no base weights, no heuristics</memory:observation>
    <memory:observation>Authorised/unauthorised states: only active chain writable, everything else read-only</memory:observation>
    <memory:observation>90 entries, 78 active, 669 tests</memory:observation>
  </memory:observations>
  <memory:prompt>Explain how the memory system works now — show all the fields</memory:prompt>
  <memory:reasoning>With provenance removed, the system is cleaner: trust is handled per-observation via basis (epistemological), not per-entity via declared labels. The gate pipeline dropped from 6 to 4 stages. The scoring formula lost the trust multiplier but retained the basis factor. The 7-space architecture and variance-weighted combiner are unchanged.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
