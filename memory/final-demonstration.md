<memory:entity schema="4" name="final-demonstration" type="knowledge" importance="6" confidence="9">
  <memory:description>Final system demonstration: 12 components verified, 108 entries, content-agnostic, all operational</memory:description>
  <memory:observations>
    <memory:observation>Parse: XML → all fields including confidence and chain extracted correctly</memory:observation>
    <memory:observation>Confidence: conf=9, conf=2, none all score 0.6600 — confirmed metadata only, not scored</memory:observation>
    <memory:observation>V12: confidence=50 correctly rejected (out of range)</memory:observation>
    <memory:observation>L0 at 2017/2000 tokens — over budget, next write will trigger eviction</memory:observation>
    <memory:observation>108 entries, 109 files, 15 MB store, 12 active chains, 11 superseded</memory:observation>
  </memory:observations>
  <memory:prompt>Demonstrate the memory system</memory:prompt>
  <memory:reasoning>All 12 components demonstrated operational: parse, authorisation, gate, confidence (metadata only), recall, relations, backlinks, embedding spaces, variance-weighted combiner, supersedes, storage layers, validation. The system is architecturally complete and content-agnostic.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
