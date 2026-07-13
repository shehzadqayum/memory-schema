---
schema: 5
importance: 8
relations:
  - USES plan-memory-v5-sota-alignment
  - USES plan-memory-system-improvement
---

DIRECTION (2026-07-05): memory-schema's next bet = the Dream Pass — scheduled consolidation over files, flagship capability: deterministic temporal validity

## Observations

- THE RECOMMENDATION: build 'the dream pass' — a scheduled consolidation actor (a Claude Code session running a consolidation skill under a SCOPED write authorization) whose first and flagship workload is TEMPORAL VALIDITY: bi-temporal validity fields in v5 frontmatter (valid_from / superseded_at / superseded_by + an optional fact KEY like 'EURUSD.bias'), deterministic WRITE-TIME supersession in 'remember' (same fact-key arriving → old fact auto-invalidated, non-lossy, no LLM judgment — the CUPMem/MemStrata pattern), recall default-filtered to currently-valid facts with an --as-of point-in-time flag
- EVIDENCE TRIANGLE for temporal-first (the sharpest in the whole survey): production adoption (Zep/Graphiti bi-temporal edge invalidation mainstream 2026, Neo4j-based like ours); quantified failure of the alternative (STALE benchmark: best frontier model 55%, memory FRAMEWORKS BELOW 10% at detecting invalidated memories; stale facts served 15-40% of the time; premise-resistance collapses 92→30% when a query presupposes the stale belief); quantified fix matching our architecture (write-side state adjudication lifts a framework 8.7%→68.0%; 'Don't Ask the LLM to Track Freshness' shows a deterministic subject-relation-object supersession rule with NO LLM call eliminates stale serving — exactly our code-structures-LLM-supplies-content CLI philosophy). Domain fit: trading biases/levels are superseded DAILY; SUPERSEDES has 5 manual uses ever; usd-strength-20260619 sat active 15 days stale
- THE DREAM PASS (industry-converged shape): OpenAI shipped Dreaming V3 (2026-06-04, background synthesis rewriting ChatGPT memories incl. temporal revision); Claude Code quietly ships Auto Dream (background subagent rewriting the memory dir after ~24h/5 sessions) + a FIRST-PARTY consolidate-memory skill (verified present in our own session's skill list); Letta runs sleep-time reflection in git worktrees over Context Repositories. All three frontier implementations = consolidation running over FILES — our exact substrate. Scope for us: distill released chains (100+ steps → durable semantic entities), merge duplicates, stamp/refresh validity on aging facts, retire never-surfaced entities, rebuild L0 — under governance the research demands (SSGM): git + audit.jsonl + write-gate + provenance hashes, all already built. Evolution must be GATED/selective (D-MEM/SAGE critique of A-MEM evolve-all; Mem0 REVERSED LLM-judged write-time deletion — archive/annotate, never destroy)
- STEERING + EXIT RAMP: (3) attribution sampling ~1/10 recalls (counterfactual: did the recalled memory change the answer? — the field's named blind spot; Mem2ActBench/HiMPO-style, cheap at 18 recalls/day) feeding telemetry-derived importance that steers the dream pass; (4) skill promotion as the Curator output — validated procedural knowledge (trading rules, A-grade setups) promoted into SKILL.md/kernel lines per the ACE playbook pattern (+10.6% agent benchmarks; Agent Skills became a cross-vendor standard, ~40 products reading SKILL.md)
- EXPLICIT NON-INVESTMENTS (the settled side of the debate): retrieval sophistication FROZEN (94% strong hits at 58 entities = measurement ceiling; sub-500-doc corpora settled in favor of curated-context + light recall; Anthropic removed vector search from Claude Code for grep-based agentic search); multi-space stays dormant (re-test at 100/250/500); heavier graph-RAG (LazyGraphRAG/HippoRAG2 justify at 10K+ docs); parametric/test-time memory (Titans/MIRAS — shipped nowhere); KV/activation memory (inaccessible on hosted APIs; prompt caching of the stable kernel+L0 prefix is the only available primitive and already exploited)

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
