<memory:entity schema="4" name="memory-fields-listing" type="knowledge" importance="6">
  <memory:description>Complete listing of all memory entity fields: 3 required, 12 LLM-authored optional, 9 system-managed</memory:description>
  <memory:observations>
    <memory:observation>Required: schema (attribute), name (attribute), description (child element)</memory:observation>
    <memory:observation>LLM-authored with embedding spaces: description, observations, prompt, reasoning, chain, name — 6 fields map 1:1 to spaces</memory:observation>
    <memory:observation>LLM-authored without spaces: type, importance, relations, source, project, provenance, body</memory:observation>
    <memory:observation>System-managed: embedding, embeddings, divergence_profile, created_at, last_accessed, access_count, verified_at, backlinks, associations</memory:observation>
    <memory:observation>Upsert behaviors: immutable (name, schema, provenance, project), replaced (description, reasoning, prompt, chain, type, importance), appended (observations), merged (relations)</memory:observation>
  </memory:observations>
  <memory:prompt>List all the memory fields</memory:prompt>
  <memory:reasoning>The field listing shows the complete data model: what the LLM controls, what the system manages, which fields have embedding spaces, and how each behaves on upsert. The 7 embedding spaces (default + 6 field-specific) cover all text content authored by the LLM.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
