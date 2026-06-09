<memory:entity schema="3" name="v3-docs-alignment-plan" type="semantic" importance="8">
  <memory:description>Plan for full v3 documentation alignment — 15 findings, 7 fix items, 8 files</memory:description>
  <memory:observations>
    <memory:observation>Documentation stuck at v2 while implementation is v3</memory:observation>
    <memory:observation>Missing: status/provenance attributes, V11/V12/R6 rules, PARENT_OF/CHILD_OF deprecation</memory:observation>
    <memory:observation>Working memory policy contradicts implementation: docs say every-response, impl is selective-write</memory:observation>
    <memory:observation>Test count stale (390→432), doctor count inconsistent (18/20/21→21)</memory:observation>
    <memory:observation>5 modules missing from technical reference</memory:observation>
  </memory:observations>
  <memory:prompt>audit all documentation and bring into alignment with implementation</memory:prompt>
  <memory:reasoning>Exhaustive audit across all documentation surfaces — user-facing docs, rules, templates, CLI docstrings, README, CHANGELOG. Root cause: v3 implementation completed in session 7 but docs not updated.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-8-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
