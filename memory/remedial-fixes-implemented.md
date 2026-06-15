<memory:entity schema="4" name="remedial-fixes-implemented" type="knowledge" importance="9" confidence="9">
  <memory:description>Remedial report fixes: A1 trust guard deleted, confidence removed from scoring, V12 added, C1-C4 fixed</memory:description>
  <memory:observations>
    <memory:observation>A1 CRITICAL: deleted ghost trust guard from On-Supersede lifecycle in schema.md</memory:observation>
    <memory:observation>B1/B2: removed confidence/10 multiplier from store.py and neo4j_store.py — confidence is write-time metadata only, preserves calibration</memory:observation>
    <memory:observation>B3: added V12 validation rule (confidence integer 1-10) in validator.py</memory:observation>
    <memory:observation>B4: documented absence semantics in schema.md and rules — "when omitted, no effect"</memory:observation>
    <memory:observation>C1: corpus "author assessment" → "importing agent's assessment"</memory:observation>
    <memory:observation>C2: removed stale "source" from overview prose, added "chain"</memory:observation>
    <memory:observation>C3: added server-managed fields list to technical-reference.md</memory:observation>
    <memory:observation>C4: "Two-verdict" → "Three-verdict" in tech-ref and write_gate.py</memory:observation>
    <memory:observation>Validation count: V1-V11 → V1-V12 across rules, template, tech-ref</memory:observation>
    <memory:observation>627 tests passing, verification checklist clean</memory:observation>
  </memory:observations>
  <memory:prompt>Implement all fixes from the remedial report</memory:prompt>
  <memory:reasoning>The key design decision: confidence removed from scoring to preserve clean calibration measurement (B2 confound). Confidence is captured at write time in the audit trail for post-hoc analysis of declared confidence vs downstream fate — without the scoring multiplier contaminating the measurement. The trust guard deletion (A1) completes the content-agnostic claim by removing the last operative trust reference.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
