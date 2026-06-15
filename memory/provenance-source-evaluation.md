<memory:entity schema="4" name="provenance-source-evaluation" type="knowledge" importance="7">
  <memory:description>Evaluation: provenance and source overlap — provenance is overloaded (binary trust), source is underused</memory:description>
  <memory:observations>
    <memory:observation>provenance: categorical trust (first-party/user/derived/ingested) — drives scoring, L0 gating, SUPERSEDES</memory:observation>
    <memory:observation>source: free text attribution (session hash, URL, path) — only required for ingested (V13)</memory:observation>
    <memory:observation>Trust hierarchy is effectively binary: trusted (3) vs ingested (1) — 4 values create illusion of granularity</memory:observation>
    <memory:observation>source is rarely set on non-ingested memories — could be valuable as general provenance trail</memory:observation>
    <memory:observation>Most memories are first-party with no source — both fields contribute nothing in the common case</memory:observation>
    <memory:observation>If redesigning: one free-form provenance field, trust inferred from content not declared labels</memory:observation>
  </memory:observations>
  <memory:prompt>Evaluate the use of both source and provenance</memory:prompt>
  <memory:reasoning>The two fields exist because trust and attribution are conceptually different (how much to trust vs where it came from). In practice, provenance carries all enforcement power while source is metadata. The 4-value provenance is effectively binary (trusted vs ingested). A cleaner design would use source more actively (record session context on every write) and simplify provenance to two values.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
