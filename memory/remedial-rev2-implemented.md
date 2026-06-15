<memory:entity schema="4" name="remedial-rev2-implemented" type="knowledge" importance="7" confidence="9">
  <memory:description>Remedial Rev 2 fixes: M1-M3 medium + L1-L4 low all implemented, 627 tests passing</memory:description>
  <memory:observations>
    <memory:observation>M1: embedding separation claim downgraded to tendency with no-enforcing-mechanism caveat</memory:observation>
    <memory:observation>M2: backend-dependent ranking documented as accepted limitation at schema.md L290</memory:observation>
    <memory:observation>M3: corpus importance "computed from source signals" → "set by importing agent"</memory:observation>
    <memory:observation>L1: schema="3" → "4" in implementation-guide test fixture</memory:observation>
    <memory:observation>L2: test count 569/33 → 627/34 + 2 integration in impl-guide + tech-ref</memory:observation>
    <memory:observation>L4: "SUPERSEDES Guards" → "SUPERSEDES Integrity" (only R7 cycle detection remains)</memory:observation>
    <memory:observation>All remedial items from both Rev 1 and Rev 2 now closed</memory:observation>
  </memory:observations>
  <memory:prompt>Implement M1-M3 and L1-L4 from remedial report rev 2</memory:prompt>
  <memory:reasoning>The medium items (M1-M3) were all correctness fixes: an unsupported claim, an undocumented divergence, and a contradictory definition. The low items (L1-L4) were mechanical. All six open items now closed. The remedial register is clear.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
