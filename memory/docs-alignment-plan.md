<memory:entity schema="3" name="docs-alignment-plan" type="semantic" importance="9">
  <memory:description>Plan for full documentation alignment — verification audit + gap coverage, 4 phases</memory:description>
  <memory:observations>
    <memory:observation>Session 11 fixed 30 issues; verification audit found 1 remaining error (hierarchy doc line 416 "v2"→"v3")</memory:observation>
    <memory:observation>Gap analysis found 41 undocumented features: CLI flags, BM25 details, L0 budget algorithm, audit trail format, reflect algorithm, degradation behavior</memory:observation>
    <memory:observation>Coverage matrix: trust multiplier in 1/10 surfaces, SUPERSEDES guards in 1/10 — critical gaps</memory:observation>
    <memory:observation>Phase 1: fix line 416. Phase 2: expand tech-ref (CLI flags, scoring, audit, degradation). Phase 3: expand schema.md (trust, L0, reflect). Phase 4: expand README (hook pipeline, degradation table)</memory:observation>
    <memory:observation>Out of scope: 21 historical memory files with schema="2" (backward compatible), stale session reports (historical)</memory:observation>
  </memory:observations>
  <memory:prompt>Verification audit + gap coverage after session 11 docs alignment</memory:prompt>
  <memory:reasoning>Session 11 achieved factual accuracy but left coverage gaps — features exist in code but aren't documented in enough surfaces for users to discover them. This plan expands existing docs rather than creating new files.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-11-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
