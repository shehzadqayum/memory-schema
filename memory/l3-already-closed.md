<memory:entity schema="4" name="l3-already-closed" type="knowledge" importance="4" confidence="9">
  <memory:description>L3 was already closed — status listed at tech-ref L55 under Server-managed, not missing</memory:description>
  <memory:observations>
    <memory:observation>tech-ref L54: Optional lists 9 author-set fields (importance through project)</memory:observation>
    <memory:observation>tech-ref L55: Server-managed lists status + 8 other system fields — status accounted for here</memory:observation>
    <memory:observation>Schema lists status as optional with active default, but behaviour is server-managed on lifecycle transitions</memory:observation>
    <memory:observation>Listing status under Server-managed (L55) is more accurate than listing it under Optional (L54)</memory:observation>
    <memory:observation>No edit needed — the report missed that L55 already accounts for status</memory:observation>
  </memory:observations>
  <memory:prompt>Evaluate the L3 fix proposal for status in optional-field list</memory:prompt>
  <memory:reasoning>The report correctly identified that status is absent from the Optional list at L54, but missed that it was already placed at L55 under Server-managed in a prior fix. Moving it back to Optional with an annotation would be less accurate than its current placement. The total field count across both lines matches the schema.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
