<memory:entity schema="4" name="memory-scope-explained" type="knowledge" importance="7" confidence="9">
  <memory:description>Memory scope: physical isolation per project (memory/ dir), logical sub-scoping via project field dot-notation</memory:description>
  <memory:observations>
    <memory:observation>Physical: each project has its own memory/ directory with MEMORY.md, store.jsonl, entity files, .active_chain</memory:observation>
    <memory:observation>Hook derives project root from file path — finds parent of memory/ directory</memory:observation>
    <memory:observation>Logical: project field enables dot-notation hierarchy (org.team.sub) with bidirectional recall and subtree-only search</memory:observation>
    <memory:observation>Plugin scope: mechanism is global (hooks, rules, skills), data is per-project (memory/ directory)</memory:observation>
    <memory:observation>No cross-project recall — project A cannot see project B's memories</memory:observation>
    <memory:observation>Shared memories: use parent project in dot-notation hierarchy for inheritance</memory:observation>
  </memory:observations>
  <memory:prompt>Would each project retain its own memories? Explain memory scope.</memory:prompt>
  <memory:reasoning>The scoping model has two layers: physical (file system — each project's memory/ directory is isolated) and logical (project field — dot-notation enables hierarchical sub-scoping within a project). The plugin packaging doesn't change this — it provides mechanism globally while data stays per-project. This is the right separation: you install the memory system once but each project builds its own knowledge base.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
