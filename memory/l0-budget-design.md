<memory:entity schema="4" name="l0-budget-design" type="semantic" importance="6">
  <memory:description>MEMORY.md L0 budget: 2000 tokens max, evicts lowest-scoring entries, groups by type</memory:description>
  <memory:observations>
    <memory:observation>Token estimation: chars / 4 (conservative approximation)</memory:observation>
    <memory:observation>Eviction order: score-based if store available (lowest importance+recency first), FIFO otherwise</memory:observation>
    <memory:observation>Progressive disclosure: entries grouped under Knowledge, Procedures, Session History headers</memory:observation>
    <memory:observation>Evicted entries persist in L1+ stores — only L0 index visibility is removed</memory:observation>
    <memory:observation>L0 gating: ingested provenance entries never enter MEMORY.md (security boundary)</memory:observation>
  </memory:observations>
  <memory:reasoning>L0 is the always-in-context index. It must stay small enough to fit in the prompt without crowding out working space. The budget enforcement ensures the index grows bounded while keeping the highest-value entries visible.</memory:reasoning>
</memory:entity>
