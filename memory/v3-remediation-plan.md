<memory:entity schema="2" name="v3-remediation-plan" type="semantic" importance="10">
  <memory:description>Memory System v3 — 28-issue remediation across 7 phases: docs, lifecycle, scoring, trust, hierarchy, retrieval, evaluation</memory:description>
  <memory:observations>
    <memory:observation>28 issues identified across 6 categories: doc drift, unimplemented semantics, scoring defects, hierarchy bugs, security/trust gaps, absent evaluation</memory:observation>
    <memory:observation>Schema v3: adds status (active/superseded/archived/quarantined) and provenance (first-party/user/ingested/derived) attributes</memory:observation>
    <memory:observation>Phase 0: doc reconciliation + docs-sync script for CI</memory:observation>
    <memory:observation>Phase 1: lifecycle — SUPERSEDES consumption, CONTRADICTS symmetry, delete/archive, MEMORY.md budget, consolidation-as-reflection</memory:observation>
    <memory:observation>Phase 2: scoring — decouple importance from scope, implement type semantics, dampening, embedding input spec</memory:observation>
    <memory:observation>Phase 3: trust — provenance field, trust-weighted retrieval, L0 gating (ingested never in MEMORY.md), write gate, audit log, hook per-project</memory:observation>
    <memory:observation>Phase 4: hierarchy — deprecate PARENT_OF/CHILD_OF, over-fetch widening, precedence repair, concurrency locks, max_depth default</memory:observation>
    <memory:observation>Phase 5: retrieval — rerank stage, BM25 hybrid, progressive disclosure for L0</memory:observation>
    <memory:observation>Phase 6: eval harness — fixture store, recall@k/MRR/nDCG, poisoning red-team suite, weight tuning blocked on this</memory:observation>
    <memory:observation>10 claims validated against codebase — all confirmed accurate</memory:observation>
    <memory:observation>Prior residual R1 (Neo4j max_depth) addressed in Phase 4.6</memory:observation>
  </memory:observations>
  <memory:reasoning>Research-anchored proposal drawing from Anthropic memory tool, context engineering guidance, managed agents memory, and memory-security literature. Phases ordered by dependency: docs first, lifecycle before trust (status needed for quarantine), eval before scoring tuning.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-6-close" type="DEPENDS_ON"/>
    <memory:relation target="package-audit-plan" type="SUPERSEDES"/>
  </memory:relations>
  <memory:source>session-7-plan</memory:source>
  <memory:project>memory-schema</memory:project>
</memory:entity>

Plan location: `.claude/plans/polymorphic-rolling-mccarthy.md`
Prior residuals: R1 Neo4j max_depth → addressing in Phase 4.6.
