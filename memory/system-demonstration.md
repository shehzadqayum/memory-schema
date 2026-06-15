<memory:entity schema="4" name="system-demonstration" type="knowledge" importance="6">
  <memory:description>Full system demonstration: 91 entries, 7 spaces, 4-stage gate, basis trust, chain lifecycle, variance-weighted scoring</memory:description>
  <memory:observations>
    <memory:observation basis="measured">91 entries (79 active), types: semantic 32, episodic 24, knowledge 15, procedural 8</memory:observation>
    <memory:observation basis="measured">Gate: ACCEPT for valid entry, REJECT for missing name — 4 stages working</memory:observation>
    <memory:observation basis="measured">Recall: scoring-formula found at 0.768 for "retrieval scoring recency decay"</memory:observation>
    <memory:observation basis="measured">Relations: chain-why-equal-weight-fails has 4 USES → evidence, evidence has 2 chain backlinks</memory:observation>
    <memory:observation basis="measured">Basis trust: 97 labelled observations (80 measured, 12 inferred, 5 reported)</memory:observation>
    <memory:observation basis="measured">Chain lifecycle: start → active, release → read-only — demonstrated end-to-end</memory:observation>
    <memory:observation>Divergence profiles not yet computed for older entries — only new hook writes get them</memory:observation>
  </memory:observations>
  <memory:prompt>Demonstrate the system</memory:prompt>
  <memory:reasoning>The demonstration exercised every component: store, spaces, authorisation, gate, scoring, recall, relations, backlinks, chain lifecycle, basis trust, and supersedes. The system is complete and operational. Older entries lack divergence profiles (predating the feature) — a reembed pass would add them.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
