<memory:entity schema="4" name="chain-access-between-entries" type="knowledge" importance="6" confidence="9">
  <memory:description>Any evidence entry reaches the reasoning chain (and all other evidence) in two hops via backlinks</memory:description>
  <memory:observations>
    <memory:observation>Path: entry ← USES ← chain (backlink) → USES → other entry (relation) — two hops</memory:observation>
    <memory:observation>The chain's observations carry the full reasoning sequence (ordered steps + conclusion)</memory:observation>
    <memory:observation>All 4 evidence entries in chain-why-equal-weight-fails are reachable from any one of them</memory:observation>
    <memory:observation>The recall cascade does this automatically at depth 1 — no special traversal code needed</memory:observation>
  </memory:observations>
  <memory:prompt>Can one memory access the chain of reasoning for the other memory?</memory:prompt>
  <memory:reasoning>The chain architecture enables reasoning access from any entry point. Backlinks (computed from USES relations) create the reverse path from evidence to chain. The chain entity contains the ordered reasoning in its observations and links to all evidence via USES. This is bidirectional graph traversal using existing infrastructure — no chain-specific code required.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
