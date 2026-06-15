## Project Memory
(entries will be added as memories are created)

### Knowledge
- [nested-agents-discussion](nested-agents-discussion.md) — Architectural discussion on nested agents using project folders as agent boundaries
- [centralize-env-vars](centralize-env-vars.md) — Plan to centralize os.environ reads into config.py — resolving session 1 residual
- [fix-env-precedence](fix-env-precedence.md) — Plan to fix env var precedence inversion, redundant import, and add hierarchy integration tests
- [docs-update-plan](docs-update-plan.md) — Plan to update all documentation for hierarchy and inheritance features
- [package-audit-plan](package-audit-plan.md) — Full package audit plan — 13 findings across CRITICAL/HIGH/MEDIUM/LOW
- [hierarchy-docs-plan](hierarchy-docs-plan.md) — Plan for hierarchy/inheritance reference doc + 7 documentation alignment fixes
- [v3-remediation-plan](v3-remediation-plan.md) — Memory System v3 — 28-issue remediation across 7 phases: docs, lifecycle, scoring, trust, hierarchy, retrieval, evaluation
- [multi-space-embed-discussion](multi-space-embed-discussion.md) — Discussion about enabling per-write multi-space embedding using M1 infrastructure
- [corpus-exploration-status](corpus-exploration-status.md) — Current memory corpus state: 40 entries, multi-space reembedded, 1 cluster found
- [type-system-explanation](type-system-explanation.md) — Explained how the type attribute works on memory entities
- [hook-env-inheritance](hook-env-inheritance.md) — Claude Code PostToolUse hook subprocesses inherit all parent env vars including VOYAGE_API_KEY
- [multi-space-cross-similarity](multi-space-cross-similarity.md) — Cross-space embedding similarity: observations↔reasoning diverge most at ~0.66
- [l0-budget-design](l0-budget-design.md) — MEMORY.md L0 budget: 2000 tokens max, evicts lowest-scoring entries, groups by type
- [scoring-formula](scoring-formula.md) — Retrieval scoring: recency × w_r + importance × w_i + cosine_sim × w_v with type/trust/basis modifiers
- [gate-pipeline-stages](gate-pipeline-stages.md) — Write gate: 6-stage pipeline producing ACCEPT/REJECT/QUARANTINE verdicts
- [storage-layer-architecture](storage-layer-architecture.md) — Five storage layers with graceful degradation: L0 MEMORY.md → L1 files/JSONL → L2 embeddings/Neo4j
- [corpus-improvement-results](corpus-improvement-results.md) — After writing knowledge-rich memories, corpus grew to 50 entries with balanced types and strong recall
- [space-evaluation-prompt-description](space-evaluation-prompt-description.md) — Evaluation: description space worth adding (high discriminative power), prompt space not (redundant with reasoning)
- [description-space-added](description-space-added.md) — Added description embedding space — 4 spaces now active per entry (4096 total dims)
- [four-space-eval-results](four-space-eval-results.md) — 4-space eval: nDCG 0.557 worse than single-space 0.608 — equal-weight averaging dilutes signal
- [system-status-snapshot](system-status-snapshot.md) — Memory system snapshot: 56 entries, 4 embedding spaces, 659 tests, single-space scoring best
- [prompt-space-added](prompt-space-added.md) — Added prompt embedding space — 5 spaces now active (5120 max dims per entry)
- [five-space-eval-results](five-space-eval-results.md) — 5-space eval: nDCG 0.555, recall 0.511 — continues downward trend with equal-weight combiner
- [query-conditioned-weighting-design](query-conditioned-weighting-design.md) — Query-conditioned weighting design: classify query by keywords, select space weight profile per type
- [query-conditioned-design-doc](query-conditioned-design-doc.md) — Full design document written for query-conditioned weighting at docs/design/query-conditioned-weighting.md

### Procedures
- [session-memory-switch](session-memory-switch.md) — Switched from built-in Claude Code memory to memory-schema system
- [working-memory-importance-change](working-memory-importance-change.md) — Changed working memory importance from tiered 7-10 to fixed 10 for all entries
- [mandatory-memory-write-rule](mandatory-memory-write-rule.md) — Memory write enforcement changed from selective to mandatory on every response
- [multi-space-activated](multi-space-activated.md) — Multi-space embedding activated in hook — all writes now embed in 3 spaces
- [bash-python-quoting-rule](bash-python-quoting-rule.md) — Never use double-quoted dict keys in f-strings inside bash python3 -c blocks
- [memory-quality-lesson](memory-quality-lesson.md) — Write facts, decisions, and patterns as semantic/procedural — not session narration as episodic

### Session History
- [deployment-verified](deployment-verified.md) — End-to-end deployment verification of memory-schema system
- [repo-created](repo-created.md) — GitHub repository created for memory-schema package
- [agent-inheritance-implemented](agent-inheritance-implemented.md) — Implemented agent rules and config inheritance with parent-absolute authority
- [inheritance-review-fixes](inheritance-review-fixes.md) — Plan for 11 inheritance code review fixes across two phases
- [session-1-close](session-1-close.md) — Session 1 complete — package setup, hierarchy, inheritance, 11 code review fixes
- [session-2-close](session-2-close.md) — Session 2 complete — centralized env var reads, resolved session 1 residual
- [session-3-close](session-3-close.md) — Session 3 complete — fixed env var precedence, redundant import, added hierarchy integration tests
- [session-4-close](session-4-close.md) — Session 4 complete — full documentation alignment, 8 items across 12 files
- [session-5-close](session-5-close.md) — Session 5 complete — full package audit, 15 items, 13 code fixes + 2 doc items
- [session-6-close](session-6-close.md) — Session 6 complete — hierarchy/inheritance reference doc + 7 documentation alignment fixes
- [out-of-session-commit](out-of-session-commit.md) — Out-of-session commit 8c12fd7 — mandatory memory write rule finalized
- [multi-space-default-confirmed](multi-space-default-confirmed.md) — Confirmed multi-space embedding is now the default hook behavior
- [out-of-session-multi-space](out-of-session-multi-space.md) — Out-of-session commit ba77a7f — multi-space embedding activated as default
- [corpus-committed](corpus-committed.md) — Committed 19 knowledge-rich memory entities as 52eac73
- [description-space-committed](description-space-committed.md) — Committed description space as f3833bd — 4 embedding spaces now active
- [out-of-session-snapshot-commit](out-of-session-snapshot-commit.md) — Out-of-session commit 5756486 — space evaluation results and system snapshot
- [prompt-space-committed](prompt-space-committed.md) — Committed prompt space as e16ec7b — 5 embedding spaces now active
