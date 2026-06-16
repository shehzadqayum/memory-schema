## Project Memory
(entries will be added as memories are created)

### Knowledge

### Procedures

### Session History

- [five-space-eval-results](five-space-eval-results.md) — 5-space eval: nDCG 0.555, recall 0.511 — continues downward trend with equal-weight combiner
- [query-conditioned-design-doc](query-conditioned-design-doc.md) — Full design document written for query-conditioned weighting at docs/design/query-conditioned-weighting.md
- [deployment-verified](deployment-verified.md) — End-to-end deployment verification of memory-schema system
- [chain-of-reasoning-discussion](chain-of-reasoning-discussion.md) — User wants to define a chain of reasoning using the memory framework — connecting memories through typed relations
- [chain-why-equal-weight-fails](chain-why-equal-weight-fails.md) — Chain: equal-weight multi-space averaging dilutes retrieval — proven through 4 experiments
- [chain-memory-quality-evolution](chain-memory-quality-evolution.md) — Chain: corpus evolved from session-metadata-heavy to knowledge-rich through deliberate type classification
- [chain-pattern-verified](chain-pattern-verified.md) — Chain entity pattern verified: chains surface as top result, cascade follows USES to evidence
- [storage-layer-architecture](storage-layer-architecture.md) — Five storage layers with graceful degradation: L0 MEMORY.md → L1 files/JSONL → L2 embeddings/Neo4j
- [chain-release-lesson](chain-release-lesson.md) — Release chains when the topic concludes — don't accumulate indefinitely into one entity
- [provenance-ambiguity](provenance-ambiguity.md) — Provenance introduces trust ambiguity — self-declared labels, effectively binary, basis attribute is the better mechanism
- [system-explanation-post-provenance](system-explanation-post-provenance.md) — Complete memory system after provenance removal: 13 LLM fields, 7 spaces, 4-stage gate, basis-based trust
- [architecture-schematic](architecture-schematic.md) — Full architecture schematic: entity schema, write pipeline, scoring, relations, chains, storage layers
- [architecture-evaluation](architecture-evaluation.md) — Architecture is improving: additive complexity (spaces, combiner, chains) followed by subtractive simplification (trust removal)
- [remedial-rev2-evaluation](remedial-rev2-evaluation.md) — Remedial Rev 2 evaluation: all critical/high closed, M1-M3 medium open, L1-L4 low open, 3 confirms ratified
- [complete-schematic](complete-schematic.md) — Complete system schematic: entity, write pipeline, retrieval, relations, chains, storage, field mapping
- [recall-example](recall-example.md) — First recall into context: variance-explanation retrieved at 0.663, accessed, used to answer
- [development-progress-report](development-progress-report.md) — Development progress: 206 commits, 23 sessions + 34 out-of-session, from v1 foundation to content-agnostic 7-space architecture
- [nested-agents-discussion](nested-agents-discussion.md) — Architectural discussion on nested agents using project folders as agent boundaries
- [session-5-close](session-5-close.md) — Session 5 complete — full package audit, 15 items, 13 code fixes + 2 doc items
- [session-6-close](session-6-close.md) — Session 6 complete — hierarchy/inheritance reference doc + 7 documentation alignment fixes
- [working-memory-importance-change](working-memory-importance-change.md) — Changed working memory importance from tiered 7-10 to fixed 10 for all entries
- [repo-created](repo-created.md) — GitHub repository created for memory-schema package
- [four-space-eval-results](four-space-eval-results.md) — 4-space eval: nDCG 0.557 worse than single-space 0.608 — equal-weight averaging dilutes signal
- [chain-pattern-formalized](chain-pattern-formalized.md) — Chain entity pattern formalized in schema spec, rules, and working guidelines
- [chain-definition](chain-definition.md) — A chain of reasoning is a sequence of memory events with a defined start (trigger) and end (conclusion)
- [memory-quality-lesson](memory-quality-lesson.md) — Write facts, decisions, and patterns as semantic/procedural — not session narration as episodic
- [chain-implementing-live-chains](chain-implementing-live-chains.md) — Chain: implementing live accumulating chain entities — formalizing the pattern in schema and rules
- [immutable-memory-evaluation](immutable-memory-evaluation.md) — Evaluation: memories should be immutable after write — no upsert, no append, each memory a snapshot
- [authorised-state-design](authorised-state-design.md) — Two memory states: unauthorised (read-only, default) and authorised (read-write, one active chain only)
- [authorised-state-implemented](authorised-state-implemented.md) — Implemented authorised/unauthorised memory states — only active chain is writable
- [package-audit-plan](package-audit-plan.md) — Full package audit plan — 13 findings across CRITICAL/HIGH/MEDIUM/LOW
- [provenance-removed](provenance-removed.md) — Provenance removed from entire framework — code, tests, and documentation synchronized
- [trust-removed-confidence-added](trust-removed-confidence-added.md) — All trust mechanisms removed, replaced with confidence (1-10) — content-agnostic architecture
- [remedial-report-evaluation](remedial-report-evaluation.md) — Evaluation of remedial report: A1 critical ghost reference confirmed, B1-B4 confidence gaps confirmed, E1-E4 decisions needed
- [remedial-fixes-implemented](remedial-fixes-implemented.md) — Remedial report fixes: A1 trust guard deleted, confidence removed from scoring, V12 added, C1-C4 fixed
- [overall-findings](overall-findings.md) — 10 key findings: equal-weight fails, variance combiner works, 1:1 mapping, trust was complexity, confidence not scored
- [recall-not-used](recall-not-used.md) — The LLM never recalled memories during this conversation — the system is write-only in practice
- [automatic-recall-implemented](automatic-recall-implemented.md) — Automatic recall implemented: rules mandate memoryschema recall before every response
- [centralize-env-vars](centralize-env-vars.md) — Plan to centralize os.environ reads into config.py — resolving session 1 residual
- [fix-env-precedence](fix-env-precedence.md) — Plan to fix env var precedence inversion, redundant import, and add hierarchy integration tests
- [docs-update-plan](docs-update-plan.md) — Plan to update all documentation for hierarchy and inheritance features
- [chain-live-accumulation-design](chain-live-accumulation-design.md) — Live chain entity: created if absent, updated every response, released at end of cycle
- [v3-remediation-plan](v3-remediation-plan.md) — Memory System v3 — 28-issue remediation across 7 phases: docs, lifecycle, scoring, trust, hierarchy, retrieval, evaluation
- [session-memory-switch](session-memory-switch.md) — Switched from built-in Claude Code memory to memory-schema system
- [agent-inheritance-implemented](agent-inheritance-implemented.md) — Implemented agent rules and config inheritance with parent-absolute authority
- [inheritance-review-fixes](inheritance-review-fixes.md) — Plan for 11 inheritance code review fixes across two phases
- [session-1-close](session-1-close.md) — Session 1 complete — package setup, hierarchy, inheritance, 11 code review fixes
- [session-2-close](session-2-close.md) — Session 2 complete — centralized env var reads, resolved session 1 residual
- [session-3-close](session-3-close.md) — Session 3 complete — fixed env var precedence, redundant import, added hierarchy integration tests
- [session-4-close](session-4-close.md) — Session 4 complete — full documentation alignment, 8 items across 12 files
- [query-conditioned-weighting-design](query-conditioned-weighting-design.md) — Query-conditioned weighting design: classify query by keywords, select space weight profile per type
- [chain-entity-design](chain-entity-design.md) — Chain entity design: a meta-memory listing ordered steps as observations with USES relations to evidence
- [memory-systems-comparison](memory-systems-comparison.md) — How this system compares: standard RAG core + novel multi-space/variance/chains/immutability on top
- [seven-spaces-explained](seven-spaces-explained.md) — Why 7 spaces: each field embedded independently so queries can match intent, facts, topic, or rationale separately
- [seven-space-applications](seven-space-applications.md) — 7 applications of multi-space architecture: faceted search, disagreement detection, intent matching, chain discovery, profiling, contradiction detection, extensible properties
- [five-applications-demonstrated](five-applications-demonstrated.md) — 5 multi-space applications demonstrated on real data: faceted search, disagreement, intent matching, profiling, contradiction
