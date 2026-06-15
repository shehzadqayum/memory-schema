<memory:entity schema="4" name="recall-not-used" type="knowledge" importance="9" confidence="10">
  <memory:description>The LLM never recalled memories during this conversation — the system is write-only in practice</memory:description>
  <memory:observations>
    <memory:observation>Not once did the LLM call memoryschema recall or store.recall() to inform a response</memory:observation>
    <memory:observation>Every response used file I/O (Read tool), code execution, or conversation context — not semantic retrieval</memory:observation>
    <memory:observation>MEMORY.md is loaded via rules but that's a static index, not ranked retrieval</memory:observation>
    <memory:observation>The recall pipeline works (demonstrated multiple times) but is not wired into response generation</memory:observation>
    <memory:observation>For recall to inform responses: needs PreToolUse hook, rules instruction to recall before answering, or MCP server</memory:observation>
  </memory:observations>
  <memory:prompt>Has the LLM been recalling any memories?</memory:prompt>
  <memory:reasoning>This is the most important finding of the session. We built a complete write pipeline (parse, embed, gate, store, index) and a complete retrieval system (scoring, variance combiner, cascade) but never connected retrieval to response generation. The system captures knowledge but doesn't use it. The next step is closing the loop: automatic recall before responses.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
