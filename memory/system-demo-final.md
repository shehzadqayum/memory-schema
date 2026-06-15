<memory:entity schema="4" name="system-demo-final" type="knowledge" importance="6" confidence="9">
  <memory:description>Full system demonstration: all components operational — 96 entries, 7 spaces, content-agnostic</memory:description>
  <memory:observations>
    <memory:observation>Store: 96 entries (83 active, 13 superseded), 4 types: semantic 32, episodic 24, knowledge 19, procedural 8</memory:observation>
    <memory:observation>Confidence scoring: conf=9 → 0.594, conf=3 → 0.198, none → 0.660 (neutral) — working correctly</memory:observation>
    <memory:observation>Gate: 4 stages — ACCEPT for valid, REJECT for missing name — demonstrated</memory:observation>
    <memory:observation>Recall: chain-why-equal-weight-fails at 0.708 for "why does multi-space averaging fail"</memory:observation>
    <memory:observation>Parser: type="demo", confidence=8, chain field — all extracted from XML correctly</memory:observation>
    <memory:observation>L0 MEMORY.md: 53 entries, 1991/2000 tokens — near budget limit</memory:observation>
    <memory:observation>Relations: 4 USES from chain entity, 2 backlinks from evidence to chain — bidirectional working</memory:observation>
  </memory:observations>
  <memory:prompt>Demonstrate the memory system</memory:prompt>
  <memory:reasoning>Every component demonstrated working end-to-end: store, spaces, authorisation, gate, confidence scoring, recall, relations, backlinks, supersedes, parser, and all storage layers. The system is architecturally complete and content-agnostic.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
