<memory:entity schema="4" name="chain-implementing-live-chains" type="knowledge" importance="8">
  <memory:description>Chain: live chains, free-form types, 1:1 field-to-space mapping (6 spaces), all docs synchronized</memory:description>
  <memory:observations>
    <memory:observation>Step 1: Defined chain as sequence of memory events, chose chain entity approach</memory:observation>
    <memory:observation>Step 2: Created retrospective chains, evolved to live accumulation model</memory:observation>
    <memory:observation>Step 3: Formalized in schema docs, rules (Rule 9), working guidelines</memory:observation>
    <memory:observation>Step 4: Freed type system — validator accepts any string, scoring recognises 3 names as incentives</memory:observation>
    <memory:observation>Step 5: Refactored to 1:1 field-to-space mapping: default + name + description + observations + prompt + reasoning</memory:observation>
    <memory:observation>Step 6: reasoning space now contains ONLY reasoning (prompt removed to its own space)</memory:observation>
    <memory:observation>Step 7: Synchronized all documentation — 6 spaces, 6-stage gate, free-form types, 1:1 mapping in schema/rules/design docs</memory:observation>
    <memory:observation>Conclusion: 6 spaces (6144 max dims), 667 tests, all docs aligned with implementation</memory:observation>
  </memory:observations>
  <memory:prompt>How should reasoning chains be captured in the memory system?</memory:prompt>
  <memory:reasoning>This chain tracked the full arc: chain concept → retrospective → live accumulation → type freedom → 1:1 space mapping → documentation sync. Each step built on the previous. The 1:1 mapping is the cleanest architecture — no field appears in two field-specific spaces, enabling precise query-conditioned weighting per field.</memory:reasoning>
  <memory:relations>
    <memory:relation target="chain-entity-design" type="USES"/>
    <memory:relation target="chain-live-accumulation-design" type="USES"/>
    <memory:relation target="chain-type-attribute-status" type="USES"/>
  </memory:relations>
</memory:entity>
