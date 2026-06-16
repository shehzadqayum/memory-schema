<memory:entity schema="4" name="user-level-plugin-scope" type="knowledge" importance="8" confidence="8">
  <memory:description>User-level plugin: 3 models — per-project data, shared user memory, or hybrid (recommend hybrid)</memory:description>
  <memory:observations>
    <memory:observation>Model A (per-project): plugin at ~/.claude/plugins/, data at each project's memory/ — complete isolation</memory:observation>
    <memory:observation>Model B (shared): all memories at ~/.claude/memory/ — cross-project knowledge but no isolation</memory:observation>
    <memory:observation>Model C (hybrid): project memory/ if exists + ~/.claude/memory/ fallback — project isolation + shared knowledge</memory:observation>
    <memory:observation>Hybrid rule: hook writes to project memory/ if exists, else ~/.claude/memory/. Recall searches project first, user fallback.</memory:observation>
    <memory:observation>User-level store becomes cross-project knowledge: debugging patterns, tool usage, preferences, decisions</memory:observation>
    <memory:observation>The project field already supports this — it tags origin for scoping at recall time</memory:observation>
  </memory:observations>
  <memory:prompt>What if the memory system is installed at user level under ~/.claude/plugins/</memory:prompt>
  <memory:reasoning>The key question is data locality, not mechanism locality. The plugin (hooks, rules, skills) should be user-level for universal availability. The data needs a dual-scope model: project-specific memories for isolation, user-level memories for cross-project knowledge. The project field provides the logical scoping; the file system provides the physical scoping. Hybrid (Model C) gets both benefits with a simple fallback rule.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
