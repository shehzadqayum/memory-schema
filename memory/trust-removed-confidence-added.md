<memory:entity schema="4" name="trust-removed-confidence-added" type="knowledge" importance="9" confidence="9">
  <memory:description>All trust mechanisms removed, replaced with confidence (1-10) — content-agnostic architecture</memory:description>
  <memory:observations>
    <memory:observation>Removed: Observation(str) subclass, VALID_BASES, VERIFICATION_RANKS, V14, Q9, basis factor, verification guard, verified_at, basis upgrade, measured checks, inferred labeling</memory:observation>
    <memory:observation>Observations are now plain strings — no per-observation metadata</memory:observation>
    <memory:observation>Added: confidence attribute (integer 1-10), scored as confidence/10 multiplier</memory:observation>
    <memory:observation>SUPERSEDES retains cycle detection (R7) but no verification guard — any memory can supersede any other</memory:observation>
    <memory:observation>627 tests passing after removal of 42 trust-related tests</memory:observation>
    <memory:observation>Architecture is now content-agnostic: no content inspection, no trust labels, author declares confidence</memory:observation>
  </memory:observations>
  <memory:prompt>Remove all trust mechanisms and redesign using confidence scoring</memory:prompt>
  <memory:reasoning>The basis system (measured/inferred/reported) inspected content to determine trust — the opposite of content agnosticism. The confidence field lets the author declare their own confidence level (1-10) without the system judging the content. This is simpler, consistent with how importance works, and eliminates the complex Observation subclass machinery.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
