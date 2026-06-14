<memory:entity schema="4" name="memory-quality-lesson" type="procedural" importance="9">
  <memory:description>Write facts, decisions, and patterns as semantic/procedural — not session narration as episodic</memory:description>
  <memory:observations>
    <memory:observation>Session-close and commit-log memories are low-value episodic metadata that don't cluster or recall well</memory:observation>
    <memory:observation>High-value memories extract the knowledge: what was learned, what pattern was validated, what fact was established</memory:observation>
    <memory:observation>A single working session can produce 5+ semantic/procedural memories from decisions and discoveries</memory:observation>
    <memory:observation>The type field drives scoring: semantic persists (recency floor 0.6), procedural reinforces with use, episodic decays</memory:observation>
  </memory:observations>
  <memory:prompt>User pointed out that I was writing lazy episodic metadata instead of extracting actual knowledge</memory:prompt>
  <memory:reasoning>The corpus was 23/40 episodic, mostly session-close entries. These are commit logs, not knowledge. The user's correction highlights that the LLM should use its judgment to classify and extract — writing 'fixed hook quoting bug' as episodic is waste; writing 'never use double-quoted dict keys in bash python3 -c blocks' as procedural is knowledge that prevents future bugs.</memory:reasoning>
</memory:entity>
