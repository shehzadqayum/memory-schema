<memory:entity schema="4" name="chain-memory-quality-evolution" type="semantic" importance="8">
  <memory:description>Chain: corpus evolved from session-metadata-heavy to knowledge-rich through deliberate type classification</memory:description>
  <memory:observations>
    <memory:observation>Step 1: Corpus was 40 entries — 23 episodic (session-close logs), 13 semantic, 4 procedural</memory:observation>
    <memory:observation>Step 2: User pointed out entries were lazy narration, not extracted knowledge</memory:observation>
    <memory:observation>Step 3: Wrote 8 knowledge-rich memories extracting facts, patterns, and decisions from the same work</memory:observation>
    <memory:observation>Step 4: Corpus shifted to 21 semantic, 6 procedural, 23 episodic — nearly balanced</memory:observation>
    <memory:observation>Step 5: Recall quality improved — knowledge entries surface at 0.65-0.77 for relevant queries</memory:observation>
    <memory:observation>Conclusion: the LLM must extract knowledge (semantic/procedural) not narrate events (episodic) to build a useful corpus</memory:observation>
  </memory:observations>
  <memory:prompt>How did the memory corpus improve from session-metadata to real knowledge?</memory:prompt>
  <memory:reasoning>The type system was always capable of differentiating — the problem was how it was applied. Session-close entries are commit logs (low recall value). Extracting 'never use double-quoted dict keys in bash python3 -c blocks' as a procedural memory creates knowledge that prevents future bugs. The shift from narrating to extracting is the key insight.</memory:reasoning>
  <memory:relations>
    <memory:relation target="memory-quality-lesson" type="USES"/>
    <memory:relation target="corpus-improvement-results" type="USES"/>
    <memory:relation target="type-system-explanation" type="USES"/>
  </memory:relations>
</memory:entity>
