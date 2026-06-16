<memory:entity schema="4" name="confidence-meaning-explained" type="knowledge" importance="5" confidence="9">
  <memory:description>Confidence is the author's degree of belief (1-10) — metadata only, does not affect scoring</memory:description>
  <memory:observations>
    <memory:observation>Confidence 9 on system-explain-with-recall: high because observations are verifiable facts about the recall loop working</memory:observation>
    <memory:observation>Not 10 because the memory is process metadata, not a durable architectural fact</memory:observation>
    <memory:observation>Confidence does NOT affect retrieval scoring — conf=9 and conf=3 produce identical rank</memory:observation>
    <memory:observation>Purpose: calibration analysis — checking declared confidence against downstream fate (superseded, recalled, contradicted)</memory:observation>
  </memory:observations>
  <memory:prompt>What is the confidence measure in the last case 9 for system-explain-with-recall</memory:prompt>
  <memory:reasoning>The user asked about the specific confidence value I assigned. This is a meta-question about authoring judgment. The answer comes from the recalled memories about the confidence design decision: it's a measurement instrument preserved immutably for future analysis, not a scoring input. The specific value (9) reflects my subjective assessment of content accuracy and value.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
