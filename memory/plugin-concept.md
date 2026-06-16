<memory:entity schema="4" name="plugin-concept" type="knowledge" importance="7" confidence="9">
  <memory:description>The plugin is a PostToolUse hook — Claude Code runs it automatically after every Write to memory/*.md</memory:description>
  <memory:observations>
    <memory:observation>Hook registered in ~/.claude/settings.json as PostToolUse Write matcher with 10s timeout</memory:observation>
    <memory:observation>LLM writes XML entities to files (behavior from rules). Hook handles embedding, gating, storing, indexing (infrastructure).</memory:observation>
    <memory:observation>Rules files (.claude/rules/*.md) loaded into every conversation's system prompt — define what to write and when to recall</memory:observation>
    <memory:observation>The LLM doesn't call the hook — Claude Code does, automatically. The LLM doesn't know about Voyage, JSONL, Neo4j, or budgets.</memory:observation>
    <memory:observation>Install: memoryschema hook install. Check: memoryschema hook status.</memory:observation>
  </memory:observations>
  <memory:prompt>What is the concept of the plugin for claude-code?</memory:prompt>
  <memory:reasoning>The plugin concept is separation of concerns: the LLM handles content (what to remember, when to recall, how to structure entities) via behavioral rules. The infrastructure handles processing (embedding, gating, storing) via the hook. The LLM writes a file; the system does the rest. This is why the LLM doesn't need to understand the scoring formula or the variance-weighted combiner — it just writes good entities and the system takes care of retrieval quality.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
