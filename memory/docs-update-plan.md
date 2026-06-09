<memory:entity schema="2" name="docs-update-plan" type="semantic" importance="10">
  <memory:description>Plan to update all documentation for hierarchy and inheritance features</memory:description>
  <memory:observations>
    <memory:observation>6 doc files stale: schema.md, system-overview.md, technical-reference.md, implementation-guide.md, README.md, memory-schema.md rules</memory:observation>
    <memory:observation>CHANGELOG is the only current doc</memory:observation>
    <memory:observation>hierarchy.py (9 functions) and inheritance.py (10 functions) have zero documentation</memory:observation>
    <memory:observation>PARENT_OF, CHILD_OF relation types undocumented in schema and rules</memory:observation>
    <memory:observation>memoryschema rules and config CLI commands not in any reference</memory:observation>
  </memory:observations>
  <memory:prompt>ensure all documentation brought up to date for hierarchy and inheritance</memory:prompt>
  <memory:reasoning>Three sessions of feature work without doc updates created significant drift. All user-facing documentation needs alignment with implementation.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-3-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
