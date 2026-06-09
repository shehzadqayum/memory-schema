<memory:entity schema="2" name="docs-update-plan" type="semantic" importance="10">
  <memory:description>Plan to align ALL documentation with implementation — 8 items, 12 files</memory:description>
  <memory:observations>
    <memory:observation>6 doc files stale: schema.md, system-overview.md, technical-reference.md, implementation-guide.md, README.md, memory-schema.md rules</memory:observation>
    <memory:observation>CHANGELOG is the only current doc</memory:observation>
    <memory:observation>hierarchy.py (9 functions) and inheritance.py (10 functions) have zero documentation</memory:observation>
    <memory:observation>PARENT_OF, CHILD_OF relation types undocumented in schema and rules</memory:observation>
    <memory:observation>memoryschema rules and config CLI commands not in any reference</memory:observation>
    <memory:observation>CLI self-docs stale: main.py docstring missing rules/config, init missing TOML, doctor missing new checks</memory:observation>
    <memory:observation>Template memory-schema.rules.tpl missing PARENT_OF/CHILD_OF</memory:observation>
    <memory:observation>3 completed plan files need historical status markers</memory:observation>
  </memory:observations>
  <memory:prompt>ensure all documentation and CLI self-docs aligned with implementation</memory:prompt>
  <memory:reasoning>Three sessions of feature work without doc updates. Expanded scope to include CLI help text, templates, and completed plan files — not just user-facing docs.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-3-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
