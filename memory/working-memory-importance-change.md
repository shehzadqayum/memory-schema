<memory:entity schema="2" name="working-memory-importance-change" type="procedural" importance="10">
  <memory:description>Changed working memory importance from tiered 7-10 to fixed 10 for all entries</memory:description>
  <memory:observations>
    <memory:observation>User requires a memory event at the end of every response</memory:observation>
    <memory:observation>Importance changed from tiered (7-10) to flat 10 for all working memory</memory:observation>
    <memory:observation>Enforcement remains strict — every response must write to memory/name.md</memory:observation>
  </memory:observations>
  <memory:prompt>we need to ensure there is a memory event at the end of each response: adjust Importance to 10</memory:prompt>
  <memory:reasoning>User wants uniform importance across all working memory to ensure nothing is deprioritized in recall. This simplifies the protocol — no judgment call needed on 7 vs 8 vs 9 vs 10.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-memory-switch" type="MODIFIES"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
