<memory:entity schema="4" name="remedial-rev2-evaluation" type="knowledge" importance="8" confidence="9">
  <memory:description>Remedial Rev 2 evaluation: all critical/high closed, M1-M3 medium open, L1-L4 low open, 3 confirms ratified</memory:description>
  <memory:observations>
    <memory:observation>All A1/B1-B4/C1-C4 verified as closed — trust/confidence model coherent</memory:observation>
    <memory:observation>M1: downgrade "embeddings separate working and corpus" to tendency — no enforcing mechanism</memory:observation>
    <memory:observation>M2: document backend-dependent ranking as accepted limitation (Neo4j +0.1 vs JSONL +0.3)</memory:observation>
    <memory:observation>M3: strike "computed from source signals" — importance is agent-assigned (content-agnostic)</memory:observation>
    <memory:observation>L1: schema="3" → "4" in implementation-guide fixture</memory:observation>
    <memory:observation>L2: test-count headline needs reconciling with breakdown</memory:observation>
    <memory:observation>L3: status in tech-ref — already fixed (server-managed fields added)</memory:observation>
    <memory:observation>L4: rename "SUPERSEDES Guards" → "SUPERSEDES Integrity" (only R7 remains)</memory:observation>
    <memory:observation>CONFIRM-1: importance double-duty accepted (retrieval weight + enforcement band)</memory:observation>
    <memory:observation>CONFIRM-2: corpus origin moot (working-memory-only deployment)</memory:observation>
    <memory:observation>CONFIRM-3: R2 closed relation set retained as structural exception</memory:observation>
  </memory:observations>
  <memory:prompt>Evaluate remedial report rev 2</memory:prompt>
  <memory:reasoning>The rev 2 report correctly identifies that all blocking defects are resolved. The remaining items are medium consistency (M1-M3), low wording (L1-L4), and design confirmations (CONFIRM 1-3). No item blocks use of the system. The three design confirmations align with the content-agnostic principle.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
