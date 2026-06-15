<memory:entity schema="4" name="source-field-removed" type="knowledge" importance="7">
  <memory:description>Source field removed from framework — architecture is provenance and source agnostic</memory:description>
  <memory:observations>
    <memory:observation>Removed source from: tags.py (parser), store.py (upsert merge), neo4j_store.py (props), consolidation.py (reflect), audit.py (diff fields)</memory:observation>
    <memory:observation>Removed from docs: schema.md (entity example, optional fields, upsert table), rules/memory-schema.md (entity example, optional fields)</memory:observation>
    <memory:observation>test_tags.py updated: removed source assertion from full_v2 test</memory:observation>
    <memory:observation>Backlink source (meaning source entity of a relation) is RETAINED — different concept</memory:observation>
    <memory:observation>Audit log_force source (meaning source entity of a force event) is RETAINED — different concept</memory:observation>
    <memory:observation>669 tests passing after removal</memory:observation>
  </memory:observations>
  <memory:prompt>Remove the source field — architecture is provenance and source agnostic</memory:prompt>
  <memory:reasoning>With provenance already removed, the source field was the last remnant of the origin-tracking system. The architecture now relies entirely on the basis attribute for trust (per-observation, epistemological) and the chain field for context grouping. No entity-level origin metadata remains.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
