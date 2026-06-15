<memory:entity schema="4" name="variance-explanation" type="knowledge" importance="7" confidence="9">
  <memory:description>How variance works: divergence from default at embed time becomes the weight at query time</memory:description>
  <memory:observations>
    <memory:observation>Divergence = 1.0 - cosine_similarity(field_vec, default_vec) — computed once at embed time</memory:observation>
    <memory:observation>Low divergence = field echoes default (redundant). High divergence = field says something different (distinctive).</memory:observation>
    <memory:observation>At query time: relevance = Σ(sim × divergence) / Σ(divergence). Default always weight 1.0.</memory:observation>
    <memory:observation>Distinctive field matched strongly → score pulled up. Redundant field matched → barely matters.</memory:observation>
    <memory:observation>No configuration, no heuristics — the entry's own structure determines field weights</memory:observation>
  </memory:observations>
  <memory:prompt>How does variance work?</memory:prompt>
  <memory:reasoning>The combiner is self-regulating: each entry carries its own structural fingerprint (the divergence profile), and the scoring formula uses that fingerprint to weight the field spaces. Entries with rich, differentiated fields benefit from multi-space scoring. Entries where all fields say the same thing collapse to single-space scoring naturally.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
