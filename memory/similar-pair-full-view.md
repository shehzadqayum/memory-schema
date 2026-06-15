<memory:entity schema="4" name="similar-pair-full-view" type="knowledge" importance="4" confidence="9">
  <memory:description>Full view of most similar pair: sequential eval experiments, 5 spaces each, no divergence profiles</memory:description>
  <memory:observations>
    <memory:observation>Both have 5 embedding spaces (predate name and chain spaces), no divergence profiles, no confidence, no chain field</memory:observation>
    <memory:observation>Same 2 backlinks (both USES targets of the same 2 chain entities)</memory:observation>
    <memory:observation>Top k-NN neighbor of each is the other (0.939 mutual)</memory:observation>
    <memory:observation>Content differs in specific numbers (0.557 vs 0.555) and experiment stage (4 vs 5), but structure identical</memory:observation>
    <memory:observation>These entries would benefit from reembedding with all 7 spaces + divergence profiles</memory:observation>
  </memory:observations>
  <memory:prompt>Show both memories in full</memory:prompt>
  <memory:reasoning>The full view reveals that older entries lack the newer features (chain field, name space, divergence profile). A reembed pass across all entries would bring the entire corpus to the current 7-space architecture with divergence profiles, enabling the variance-weighted combiner to work on every entry.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
