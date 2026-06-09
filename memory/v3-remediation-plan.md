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

## Git Operations

- `a1aff31` — `[S1] Memory System v3 — Remediation & Research Alignment` — Plan committed and pushed
- `1fa9148` — `[S2] Phase 0 — docs-sync script + remaining count fixes` — docs_sync.py, impl-guide stale count, hook scope warning
- `8b9411e` — `[S2] Phase 1.1 — Add status field (schema v3)` — VALID_STATUSES, V11 check, status filtering in search/recall
- `e5e7757` — `[S2] Phase 1.2 — SUPERSEDES consumption + CONTRADICTS symmetry` — relation side-effects in both stores
- `e35ac2d` — `[S2] Phase 1.3 — Delete/archive ops + R6 referential integrity` — full delete cleanup, archive command, R6 validation
- `13cf5cc` — `[S2] Phase 1.4 — MEMORY.md token budget and eviction` — l0_budget.py, hook integration, configurable budget
- `94b43d6` — `[S2] Phase 1.5 — Reflection (episodic→semantic synthesis)` — reflect(), clustering, LLM/mechanical synthesis
- `a01d126` — `[S2] Phase 2.1 — Decouple importance from scope, selective writes` — rules + template + system-overview
- `3db1da8` — `[S2] Phase 2.2 — Implement type-dependent recency semantics` — semantic=1.0, procedural=access-reinforced
- `57c3cc8` — `[S2] Phase 2.3 — Log-scale hub bonus dampening` — 0.05*ln(1+backlinks)
- `63962ec` — `[S2] Phase 2.4 — Specify and standardize embedding input` — schema spec, name added, Q8 reasoning check
- `4ab8504` — `[S2] Phase 3.1 — Add provenance field (schema v3)` — VALID_PROVENANCES, V12, upsert merge
- `5707e15` — `[S2] Phase 3.2 — Trust-weighted retrieval and L0 gating` — trust multipliers, ingested blocked from MEMORY.md
- `d622367` — `[S2] Phase 3.3 — Pre-consolidation write gate` — write_gate.py, provenance enforcement, consistency probe
- `87925aa` — `[S2] Phase 3.4 — Append-only audit log for mutations` — audit.py, store integration
- `03229db` — `[S2] Phase 3.5 — Per-project hook, random password, rules attestation` — hygiene fixes
- `f0502aa` — `[S2] Phase 4.1 — Deprecate PARENT_OF/CHILD_OF relations` — hierarchy single source
- `4d89486` — `[S2] Phase 4.2 — Dot-boundary prefix regression tests` — 18 new tests, 408 total
- `e432914` — `[S2] Phase 4.3 — Iterative over-fetch widening` — 3x→9x→100x fallback
- `68853ee` — `[S2] Phase 4.4 — Precedence repair: CLI > env > TOML` — explicit beats ambient
- `34eb41b` — `[S2] Phase 4.5 — Advisory file lock for JSONL concurrency` — fcntl LOCK_EX
- `a3fe9c5` — `[S2] Phase 4.6 — Finite max_inherit_depth default` — default=3, TOML configurable
- `695dde4` — `[S2] Phase 5.1 — Wire Voyage reranker into recall path` — 3x over-fetch → rerank → top-k
- `8f7d1ab` — `[S2] Phase 5.2 — BM25 lexical channel replaces substring boost` — pure-Python BM25
- `adc8c71` — `[S2] Phase 5.3 — Progressive disclosure with category grouping` — Knowledge/Procedures/History headers
- `6cfa4d5` — `[S2] Phase 6 — Evaluation harness with fixtures, metrics, poisoning suite` — 19 eval tests, 427 total
- (pending) — `[S3] Session 7 checkpoint — 25/25 audited PASS` — Feedback commit
