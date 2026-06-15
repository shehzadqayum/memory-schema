<memory:entity schema="4" name="most-similar-pair" type="knowledge" importance="5" confidence="9">
  <memory:description>Most similar pair: four-space-eval and five-space-eval at 0.9393 — differentiated by description and prompt spaces</memory:description>
  <memory:observations>
    <memory:observation>Default similarity 0.9393 — sequential experiments measuring the same thing</memory:observation>
    <memory:observation>Per-space: observations 0.94, reasoning 0.91, description 0.73, prompt 0.64</memory:observation>
    <memory:observation>Description and prompt are most divergent — capture "4-space" vs "5-space" distinction</memory:observation>
    <memory:observation>The 1:1 field-to-space architecture enables differentiating entries that blend together in default space</memory:observation>
  </memory:observations>
  <memory:prompt>Show two of the most similar memories</memory:prompt>
  <memory:reasoning>The pair demonstrates why field-specific spaces matter: the default blend is 0.94 (nearly identical), but description drops to 0.73 and prompt to 0.64. A query targeting the specific experiment number would activate the description space, differentiating two entries that are otherwise indistinguishable in the default blend.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
