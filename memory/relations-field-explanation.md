<memory:entity schema="4" name="relations-field-explanation" type="knowledge" importance="5">
  <memory:description>The relations field: container of typed links to other memories, merged on upsert, not embedded</memory:description>
  <memory:observations>
    <memory:observation>Each relation has target (memory name) and type (one of 7 relation types)</memory:observation>
    <memory:observation>Upsert: merged with deduplication (same target+type not duplicated)</memory:observation>
    <memory:observation>compute_backlinks() creates reverse links on target entities</memory:observation>
    <memory:observation>Not an embedding space — relations are structural (name + type), not semantic text</memory:observation>
    <memory:observation>Traversed in recall cascade graph walk, not via vector similarity</memory:observation>
  </memory:observations>
  <memory:prompt>Explain the relations field</memory:prompt>
  <memory:reasoning>Relations are the graph edges of the memory system. They're authored as forward links, computed as backlinks, and traversed during recall. They're distinct from embedding spaces — they encode explicit connections between memories rather than semantic content. The deduplication on merge prevents relation bloat on upsert.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
