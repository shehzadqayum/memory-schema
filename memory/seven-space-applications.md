<memory:entity schema="4" name="seven-space-applications" type="knowledge" importance="9" confidence="8">
  <memory:description>7 applications of multi-space architecture: faceted search, disagreement detection, intent matching, chain discovery, profiling, contradiction detection, extensible properties</memory:description>
  <memory:observations>
    <memory:observation>Faceted search: --space flag to search only prompt, observations, reasoning, chain, or description independently</memory:observation>
    <memory:observation>Cross-space disagreement: low observations↔reasoning similarity flags internal inconsistency without reading content</memory:observation>
    <memory:observation>Intent matching: prompt space enables question-to-question matching (not just content matching)</memory:observation>
    <memory:observation>Chain discovery: chain space clusters entries by investigation regardless of content</memory:observation>
    <memory:observation>Entry profiling: divergence profiles create automatic typology (thin/rich/intent-heavy/fact-heavy) from vector geometry</memory:observation>
    <memory:observation>Cross-field contradiction: gap between description similarity and observation similarity flags entries needing reconciliation</memory:observation>
    <memory:observation>Extensible: add a field → it gets a space. Potential: context, outcome, audience, domain</memory:observation>
    <memory:observation>Key insight: each memory is not a point but a STRUCTURE with independently queryable facets. The data is already there.</memory:observation>
  </memory:observations>
  <memory:prompt>Suggest a proposal for better usage of this data — what can we achieve with 7 spaces?</memory:prompt>
  <memory:reasoning>The 7-space architecture was built for scoring (variance-weighted combiner), but the per-space vectors enable applications beyond retrieval ranking: faceted search, quality checking, intent matching, automatic categorization, and contradiction detection. These are all queries against existing data — no new embedding infrastructure needed. The extensibility (add field → get space) means the architecture scales to new use cases by adding entity fields.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
