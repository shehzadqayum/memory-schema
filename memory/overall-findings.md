<memory:entity schema="4" name="overall-findings" type="knowledge" importance="9" confidence="9">
  <memory:description>10 key findings: equal-weight fails, variance combiner works, 1:1 mapping, trust was complexity, confidence not scored</memory:description>
  <memory:observations>
    <memory:observation>Equal-weight multi-space averaging monotonically degrades retrieval: single 0.608 → 3-space 0.601 → 4-space 0.557 → 5-space 0.555</memory:observation>
    <memory:observation>Variance-weighted combiner (divergence from default = weight) is self-regulating — no configuration needed</memory:observation>
    <memory:observation>1:1 field-to-space mapping is cleanest: description most discriminative (0.35-0.47 gap), prompt most divergent (0.40 avg)</memory:observation>
    <memory:observation>3 trust systems (provenance+basis+source) were overlapping complexity — removal simplified gate 6→4, eliminated Observation subclass</memory:observation>
    <memory:observation>Confidence must not score — calibration confound: scoring alters the outcomes used to evaluate confidence accuracy</memory:observation>
    <memory:observation>Chain entities work: ordered reasoning in observations, USES to evidence, backlinks for reverse access (2 hops)</memory:observation>
    <memory:observation>Immutability with single writable chain prevents unbounded accumulation (148-observation anti-pattern proved the need)</memory:observation>
    <memory:observation>Free-form type produced 4 organic types: knowledge 36, semantic 32, episodic 24, procedural 8</memory:observation>
    <memory:observation>Documentation must track implementation not prescribe — 3 remedial passes needed for alignment</memory:observation>
    <memory:observation>Pattern: additive complexity (spaces, combiner, chains) then subtractive simplification (trust removal) = more capability, less machinery</memory:observation>
  </memory:observations>
  <memory:prompt>What are our findings overall?</memory:prompt>
  <memory:reasoning>The session evolved the system from 1 space with 3 trust mechanisms to 7 spaces with zero trust mechanisms. The key insight was that equal-weight averaging was the bottleneck, not the spaces — and that trust was overlapping complexity that could be replaced by a single non-scoring metadata field. The architecture is now content-agnostic, self-regulating (variance combiner), and immutable by default (authorisation states).</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
