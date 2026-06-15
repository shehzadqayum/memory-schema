<memory:entity schema="4" name="relations-explanation" type="knowledge" importance="7">
  <memory:description>7 relation types: USES, MODIFIES, SUPERSEDES, DEPENDS_ON, INFORMS, CONTRADICTS, MITIGATES</memory:description>
  <memory:observations>
    <memory:observation>4 informational (USES, MODIFIES, DEPENDS_ON, INFORMS) — create links, no side effects</memory:observation>
    <memory:observation>SUPERSEDES: marks target superseded, trust+verification guards, cycle detection, force record</memory:observation>
    <memory:observation>CONTRADICTS: symmetric — auto-creates reverse edge on target, logs force record</memory:observation>
    <memory:observation>MITIGATES: target stays active but gets 0.95 score dampening</memory:observation>
    <memory:observation>Relations create forward links, backlinks are computed as reverse. Both traversed in recall cascade.</memory:observation>
    <memory:observation>Hub bonus: +0.05 × ln(1 + backlinks) — more connected memories score higher</memory:observation>
    <memory:observation>Chain entities use USES to link to evidence — backlinks enable reverse traversal from evidence to chain</memory:observation>
  </memory:observations>
  <memory:prompt>Explain relations</memory:prompt>
  <memory:reasoning>Relations are the graph structure of the memory system. Most are informational links that enable cascade traversal. SUPERSEDES, CONTRADICTS, and MITIGATES have side effects that alter scoring or status. The USES relation is the most important for chains — it creates the bidirectional link between chain entities and their evidence.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
