## Project Memory
(entries will be added as memories are created)

### Knowledge
- [prompt-space-added](prompt-space-added.md) — Added prompt embedding space — 5 spaces now active (5120 max dims per entry)
- [corpus-improvement-results](corpus-improvement-results.md) — After writing knowledge-rich memories, corpus grew to 50 entries with balanced types and strong recall
- [hook-env-inheritance](hook-env-inheritance.md) — Claude Code PostToolUse hook subprocesses inherit all parent env vars including VOYAGE_API_KEY
- [l0-budget-design](l0-budget-design.md) — MEMORY.md L0 budget: 2000 tokens max, evicts lowest-scoring entries, groups by type
- [multi-space-cross-similarity](multi-space-cross-similarity.md) — Cross-space embedding similarity: observations↔reasoning diverge most at ~0.66
- [description-space-added](description-space-added.md) — Added description embedding space — 4 spaces now active per entry (4096 total dims)
- [space-evaluation-prompt-description](space-evaluation-prompt-description.md) — Evaluation: description space worth adding (high discriminative power), prompt space not (redundant with reasoning)
- [chain-not-formalized](chain-not-formalized.md) — Chain entity pattern is working but not documented in schema rules, design docs, or working memory guidelines
- [chain-type-attribute-status](chain-type-attribute-status.md) — Type attribute and fields partially resolved — chain pattern formalized but type guidance not updated for chain model
- [scoring-formula](scoring-formula.md) — Retrieval scoring: recency × w_r + importance × w_i + cosine_sim × w_v with type/trust/basis modifiers
- [gate-pipeline-stages](gate-pipeline-stages.md) — Write gate: 6-stage pipeline producing ACCEPT/REJECT/QUARANTINE verdicts
- [chain-hook-embedding-investigation](chain-hook-embedding-investigation.md) — Chain: hook embedding appeared broken but was actually a bash quoting issue — 4-step debugging sequence
- [hierarchy-docs-plan](hierarchy-docs-plan.md) — Plan for hierarchy/inheritance reference doc + 7 documentation alignment fixes
- [five-space-eval-results](five-space-eval-results.md) — 5-space eval: nDCG 0.555, recall 0.511 — continues downward trend with equal-weight combiner
- [query-conditioned-design-doc](query-conditioned-design-doc.md) — Full design document written for query-conditioned weighting at docs/design/query-conditioned-weighting.md
- [storage-layer-architecture](storage-layer-architecture.md) — Five storage layers with graceful degradation: L0 MEMORY.md → L1 files/JSONL → L2 embeddings/Neo4j
- [chain-of-reasoning-discussion](chain-of-reasoning-discussion.md) — User wants to define a chain of reasoning using the memory framework — connecting memories through typed relations
- [chain-why-equal-weight-fails](chain-why-equal-weight-fails.md) — Chain: equal-weight multi-space averaging dilutes retrieval — proven through 4 experiments
- [chain-memory-quality-evolution](chain-memory-quality-evolution.md) — Chain: corpus evolved from session-metadata-heavy to knowledge-rich through deliberate type classification
- [nested-agents-discussion](nested-agents-discussion.md) — Architectural discussion on nested agents using project folders as agent boundaries
- [four-space-eval-results](four-space-eval-results.md) — 4-space eval: nDCG 0.557 worse than single-space 0.608 — equal-weight averaging dilutes signal
- [chain-implementing-live-chains](chain-implementing-live-chains.md) — Chain: implementing live accumulating chain entities — formalizing the pattern in schema and rules
- [chain-pattern-formalized](chain-pattern-formalized.md) — Chain entity pattern formalized in schema spec, rules, and working guidelines
- [package-audit-plan](package-audit-plan.md) — Full package audit plan — 13 findings across CRITICAL/HIGH/MEDIUM/LOW
- [chain-definition](chain-definition.md) — A chain of reasoning is a sequence of memory events with a defined start (trigger) and end (conclusion)
- [immutable-memory-evaluation](immutable-memory-evaluation.md) — Evaluation: memories should be immutable after write — no upsert, no append, each memory a snapshot
- [authorised-state-design](authorised-state-design.md) — Two memory states: unauthorised (read-only, default) and authorised (read-write, one active chain only)
- [authorised-state-implemented](authorised-state-implemented.md) — Implemented authorised/unauthorised memory states — only active chain is writable
- [centralize-env-vars](centralize-env-vars.md) — Plan to centralize os.environ reads into config.py — resolving session 1 residual
- [fix-env-precedence](fix-env-precedence.md) — Plan to fix env var precedence inversion, redundant import, and add hierarchy integration tests
- [docs-update-plan](docs-update-plan.md) — Plan to update all documentation for hierarchy and inheritance features
- [query-conditioned-weighting-design](query-conditioned-weighting-design.md) — Query-conditioned weighting design: classify query by keywords, select space weight profile per type
- [v3-remediation-plan](v3-remediation-plan.md) — Memory System v3 — 28-issue remediation across 7 phases: docs, lifecycle, scoring, trust, hierarchy, retrieval, evaluation
- [chain-live-accumulation-design](chain-live-accumulation-design.md) — Live chain entity: created if absent, updated every response, released at end of cycle
- [chain-entity-design](chain-entity-design.md) — Chain entity design: a meta-memory listing ordered steps as observations with USES relations to evidence

### Procedures
- [multi-space-activated](multi-space-activated.md) — Multi-space embedding activated in hook — all writes now embed in 3 spaces
- [bash-python-quoting-rule](bash-python-quoting-rule.md) — Never use double-quoted dict keys in f-strings inside bash python3 -c blocks
- [mandatory-memory-write-rule](mandatory-memory-write-rule.md) — Memory write enforcement changed from selective to mandatory on every response
- [chain-pattern-verified](chain-pattern-verified.md) — Chain entity pattern verified: chains surface as top result, cascade follows USES to evidence
- [chain-release-lesson](chain-release-lesson.md) — Release chains when the topic concludes — don't accumulate indefinitely into one entity
- [working-memory-importance-change](working-memory-importance-change.md) — Changed working memory importance from tiered 7-10 to fixed 10 for all entries
- [memory-quality-lesson](memory-quality-lesson.md) — Write facts, decisions, and patterns as semantic/procedural — not session narration as episodic
- [session-memory-switch](session-memory-switch.md) — Switched from built-in Claude Code memory to memory-schema system

### Session History
- [deployment-verified](deployment-verified.md) — End-to-end deployment verification of memory-schema system
- [session-5-close](session-5-close.md) — Session 5 complete — full package audit, 15 items, 13 code fixes + 2 doc items
- [session-6-close](session-6-close.md) — Session 6 complete — hierarchy/inheritance reference doc + 7 documentation alignment fixes
- [repo-created](repo-created.md) — GitHub repository created for memory-schema package
- [agent-inheritance-implemented](agent-inheritance-implemented.md) — Implemented agent rules and config inheritance with parent-absolute authority
- [inheritance-review-fixes](inheritance-review-fixes.md) — Plan for 11 inheritance code review fixes across two phases
- [session-1-close](session-1-close.md) — Session 1 complete — package setup, hierarchy, inheritance, 11 code review fixes
- [session-2-close](session-2-close.md) — Session 2 complete — centralized env var reads, resolved session 1 residual
- [session-3-close](session-3-close.md) — Session 3 complete — fixed env var precedence, redundant import, added hierarchy integration tests
- [session-4-close](session-4-close.md) — Session 4 complete — full documentation alignment, 8 items across 12 files
