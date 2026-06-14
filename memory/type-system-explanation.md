<memory:entity schema="4" name="type-system-explanation" type="semantic" importance="4">
  <memory:description>Explained how the type attribute works on memory entities</memory:description>
  <memory:observations>
    <memory:observation>Type is an XML attribute on memory:entity — semantic, episodic, or procedural</memory:observation>
    <memory:observation>Type affects scoring: semantic has recency floor 0.6, episodic standard decay, procedural access-reinforced</memory:observation>
    <memory:observation>Type drives MEMORY.md progressive disclosure grouping (Knowledge, Session History, Procedures)</memory:observation>
    <memory:observation>Current corpus: 13 semantic, 23 episodic, 4 procedural out of 40 total</memory:observation>
  </memory:observations>
  <memory:prompt>User asked how type currently works and whether the LLM specifies it</memory:prompt>
  <memory:reasoning>The type system is already functional. The LLM sets type on every entity write. The question may be about whether the type selection is good or whether a different taxonomy would be better.</memory:reasoning>
</memory:entity>
