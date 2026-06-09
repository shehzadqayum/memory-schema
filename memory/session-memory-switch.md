<memory:entity schema="2" name="session-memory-switch" type="procedural" importance="10">
  <memory:description>Switched from built-in Claude Code memory to memory-schema system</memory:description>
  <memory:observations>
    <memory:observation>autoMemoryEnabled set to false in ~/.claude/settings.json</memory:observation>
    <memory:observation>Built-in frontmatter memory at ~/.claude/projects/.../memory/ suspended</memory:observation>
    <memory:observation>memory-schema XML entity system is now the active memory backend</memory:observation>
    <memory:observation>Every response must end with a memory write to memory/name.md per working memory guidelines</memory:observation>
    <memory:observation>Revert by setting autoMemoryEnabled back to true if memory-schema becomes non-functional</memory:observation>
  </memory:observations>
  <memory:reasoning>User explicitly requested suspending built-in memory in favor of memory-schema. The two systems use incompatible formats (YAML frontmatter vs XML entity). Running both causes confusion and hook failures. memory-schema provides richer capabilities: embeddings, Neo4j graph, semantic recall, typed relations.</memory:reasoning>
  <memory:project>memory-schema</memory:project>
</memory:entity>
