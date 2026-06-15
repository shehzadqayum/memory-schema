<memory:entity schema="4" name="chain-why-equal-weight-fails" type="semantic" importance="8">
  <memory:description>Chain: equal-weight multi-space averaging dilutes retrieval — proven through 4 experiments</memory:description>
  <memory:observations>
    <memory:observation>Step 1: M1 built 3 field spaces (observations, reasoning) with equal-weight combiner</memory:observation>
    <memory:observation>Step 2: 3-space eval showed nDCG 0.601 vs single-space 0.608 — slight regression</memory:observation>
    <memory:observation>Step 3: Added description space (4th). 4-space nDCG dropped to 0.557</memory:observation>
    <memory:observation>Step 4: Added prompt space (5th). 5-space nDCG dropped to 0.555</memory:observation>
    <memory:observation>Step 5: desc+default weighted profile achieved nDCG 0.747 — beating all equal-weight configs</memory:observation>
    <memory:observation>Conclusion: the spaces have value but the combiner must weight them, not average equally</memory:observation>
  </memory:observations>
  <memory:prompt>Why does adding more embedding spaces make retrieval worse?</memory:prompt>
  <memory:reasoning>Each experiment added a space and measured the result. The monotonic degradation (0.608 → 0.601 → 0.557 → 0.555) proved the combiner is the bottleneck. The desc+default weighted profile (0.747) proved the spaces themselves are valuable when weighted correctly.</memory:reasoning>
  <memory:relations>
    <memory:relation target="multi-space-cross-similarity" type="USES"/>
    <memory:relation target="four-space-eval-results" type="USES"/>
    <memory:relation target="five-space-eval-results" type="USES"/>
    <memory:relation target="query-conditioned-weighting-design" type="USES"/>
  </memory:relations>
</memory:entity>
