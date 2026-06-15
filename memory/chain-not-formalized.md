<memory:entity schema="4" name="chain-not-formalized" type="semantic" importance="6">
  <memory:description>Chain entity pattern is working but not documented in schema rules, design docs, or working memory guidelines</memory:description>
  <memory:observations>
    <memory:observation>Pattern exists only as ad-hoc memories and conversation knowledge — no formal spec</memory:observation>
    <memory:observation>Needs documentation in: .claude/rules/memory-schema.md, docs/schema.md, .claude/rules/memory-working.md</memory:observation>
    <memory:observation>Three locations needed: schema (what a chain entity looks like), working guidelines (when to create one), design docs (the pattern rationale)</memory:observation>
  </memory:observations>
  <memory:prompt>User asked if chain entity pattern has been documented and formalized</memory:prompt>
  <memory:reasoning>The pattern works empirically (3 chains tested, recall scores 0.72-0.78) but isn't codified. Without formalization, future sessions won't know the pattern exists or how to apply it. The schema rules and working guidelines are loaded into every conversation — adding chain guidance there ensures it persists.</memory:reasoning>
</memory:entity>
