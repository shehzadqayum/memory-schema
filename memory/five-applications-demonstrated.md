<memory:entity schema="4" name="five-applications-demonstrated" type="knowledge" importance="8" confidence="9">
  <memory:description>5 multi-space applications demonstrated on real data: faceted search, disagreement, intent matching, profiling, contradiction</memory:description>
  <memory:observations>
    <memory:observation>Faceted search: prompt-space reranks results — bash-python-quoting-rule jumps from #3 to #1 for hook-related query</memory:observation>
    <memory:observation>Cross-field: session-2-close has obs↔rea similarity 0.234 (most divergent), chain-live-accumulation-design 0.881 (most aligned)</memory:observation>
    <memory:observation>Intent matching: "why remove trust?" matches stored prompt "Remove all trust mechanisms..." at 0.671 — question-to-question</memory:observation>
    <memory:observation>Profiling: 16 rich, 14 intent-heavy, 9 fact-heavy — categories from vector geometry, no labels</memory:observation>
    <memory:observation>Contradiction: 6 pairs with description sim > 0.6 but observation gap > 0.15 — same topic, different facts</memory:observation>
    <memory:observation>All applications run against existing data — no new infrastructure needed, just queries against 7-space vectors</memory:observation>
  </memory:observations>
  <memory:prompt>Show examples of faceted search, cross-field analysis, intent matching, structural profiling, contradiction detection</memory:prompt>
  <memory:reasoning>Each application demonstrates a capability that single-vector systems cannot provide. Faceted search differentiates intent from content. Cross-field analysis detects internal inconsistency. Intent matching finds prior questions. Profiling categorizes without labels. Contradiction detection finds update candidates. All from the same 7 vectors per entry.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
