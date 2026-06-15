<memory:entity schema="4" name="remedial-report-evaluation" type="knowledge" importance="9" confidence="8">
  <memory:description>Evaluation of remedial report: A1 critical ghost reference confirmed, B1-B4 confidence gaps confirmed, E1-E4 decisions needed</memory:description>
  <memory:observations>
    <memory:observation>A1 CRITICAL: schema.md L410 still has "Trust guard checked" — ghost reference from provenance removal, code already removed</memory:observation>
    <memory:observation>B1: confidence scores in code (store.py) but undocumented in schema.md scoring section</memory:observation>
    <memory:observation>B2: confidence in scoring creates calibration confound — low-confidence entries less retrievable, contaminating fate measurement</memory:observation>
    <memory:observation>B3: no V12 validation rule for confidence range (1-10) — out-of-range values unchecked</memory:observation>
    <memory:observation>B4: no default/absence semantics for confidence stated in schema</memory:observation>
    <memory:observation>Recommendation E2: remove confidence from scoring to preserve clean calibration — capture at write time for analysis only</memory:observation>
    <memory:observation>Recommendation E4: retain R2 (closed relation types) as structural exception — relations drive graph traversal</memory:observation>
    <memory:observation>C1-C4 and D1-D7 confirmed as accurate findings</memory:observation>
  </memory:observations>
  <memory:prompt>Evaluate the remedial report</memory:prompt>
  <memory:reasoning>The report is methodologically rigorous — line-anchored, severity-graded, with clear fix/decision separation. The A1 critical is a genuine contradiction (trust guard reference + content-agnostic claim). The B2 calibration confound is the deepest insight: confidence affecting retrieval contaminates the measurement of confidence accuracy. The cleanest resolution is to remove confidence from scoring entirely — it becomes metadata for post-hoc analysis, not a live scoring input.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
