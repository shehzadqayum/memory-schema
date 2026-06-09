<memory:entity schema="2" name="hierarchy-docs-plan" type="semantic" importance="8">
  <memory:description>Plan for hierarchy/inheritance reference doc + 7 documentation alignment fixes</memory:description>
  <memory:observations>
    <memory:observation>9 items: 1 new reference doc, 1 plan doc move, 7 alignment fixes across 12 files</memory:observation>
    <memory:observation>New doc: docs/hierarchy-and-inheritance.md — standalone feature guide with examples, API, troubleshooting</memory:observation>
    <memory:observation>Alignment fixes: doctor Python version, stale counts, phantom memory/user/ path, importance 8-10 vs 10, scoring bonuses</memory:observation>
    <memory:observation>Cross-references: forward refs from README, system-overview, tech-ref, impl-guide to new doc</memory:observation>
  </memory:observations>
  <memory:relations>
    <memory:relation target="package-audit-plan" type="DEPENDS_ON"/>
    <memory:relation target="session-5-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:source>session-6-plan</memory:source>
  <memory:project>memory-schema</memory:project>
</memory:entity>

Plan location: `.claude/plans/polymorphic-rolling-mccarthy.md`
Prior residuals: R1 Neo4j max_depth → deferring (architectural).
