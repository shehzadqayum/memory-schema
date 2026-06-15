<memory:entity schema="4" name="docs-sync-authorisation" type="knowledge" importance="5">
  <memory:description>Documentation synchronized with authorised/unauthorised memory state model</memory:description>
  <memory:observations>
    <memory:observation>docs/schema.md: authorisation gate in upsert semantics, chain lifecycle with CLI commands, behavioral spec updated</memory:observation>
    <memory:observation>.claude/rules/memory-schema.md: Rule 6 authorisation gate + chain field, Rule 9 start/release lifecycle</memory:observation>
    <memory:observation>.claude/rules/memory-working.md: lifecycle with commands, .active_chain file, standalone memories read-only</memory:observation>
  </memory:observations>
  <memory:prompt>Synchronise all documentation with authorised/unauthorised implementation</memory:prompt>
  <memory:reasoning>The authorisation model was implemented in code but absent from all documentation. Three files updated: source of truth (schema.md), derived rules, and working guidelines. Authorisation is now documented as a prerequisite for upsert throughout the write pipeline.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
