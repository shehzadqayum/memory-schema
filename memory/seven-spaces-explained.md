<memory:entity schema="4" name="seven-spaces-explained" type="knowledge" importance="7" confidence="9">
  <memory:description>Why 7 spaces: each field embedded independently so queries can match intent, facts, topic, or rationale separately</memory:description>
  <memory:observations>
    <memory:observation>Most systems: 1 vector per entry (all text blended). This system: 7 vectors (one per field + default blend).</memory:observation>
    <memory:observation>Benefit: "what did the user ask?" matches prompt space, "what facts exist?" matches observations space — different queries activate different fields</memory:observation>
    <memory:observation>Description diverges from default by 0.21-0.35 — captures what's actually different between topically similar entries</memory:observation>
    <memory:observation>Variance-weighted: divergence from default IS the weight. Distinctive fields amplified (prompt at 0.60 weight), redundant fields suppressed (observations at 0.08)</memory:observation>
    <memory:observation>7 × 1024 = 7168 dimensions per entry — more storage and compute, but enables field-level discrimination</memory:observation>
  </memory:observations>
  <memory:prompt>Explain 7 independent spaces per entry</memory:prompt>
  <memory:reasoning>The multi-space architecture exists because a single blended vector loses field-level information. When everything is mixed into one vector, you can't tell whether a query matched the user's intent, the observed facts, or the rationale. Separate spaces preserve this distinction. The variance-weighted combiner then decides at query time which fields matter most for each specific query-entry pair.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
