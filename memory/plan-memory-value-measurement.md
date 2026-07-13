---
schema: 5
importance: 7
relations:
  - USES memory-module-value-evaluation
  - USES seven-space-scoring-activated
---

PLAN (2026-06-30, not yet built)…

## Summary

PLAN (2026-06-30, not yet built): three measurement moves to convert the memory module's ASSUMED benefit into MEASURED benefit — (1) log recall usage, (2) a multi-space ablation harness gated on corpus size, (3) a Neo4j-vs-JSONL benchmark + decision. Sequenced 1->2->3; all low-blast-radius (logging + scripts + a decision doc).

## Observations

- MOVE 1 (foundation, do first) — MEASURE RECALL USAGE. Problem: access_count=0/44, so the central claim 'memory helps across sessions' is unmeasured. Build an append-only recall telemetry log (separate from scoring) at the CLI recall seam (cli/memory_cmd.py recall): record {ts, query, top-k name+score, backend, degraded}. Add a `recall-stats` reader: recalls/session, hit-score distribution, most/least-surfaced memories, NEVER-surfaced (dead-weight) entities, % recalls with a strong hit (score > threshold). Optionally (opt-in flag) bump access_count on seed hits so the procedural scoring finally has data — keep OFF during the measurement window to avoid distorting it. Honest limit: this measures RETRIEVAL, not UTILITY (did the recalled memory change the answer? — needs response-attribution, a later second-order metric). Decision rule (pre-committed): after ~10-20 sessions, if recall is rarely run or rarely returns a strong hit -> the store is write-only -> re-scope (write less / trigger recall more); if frequent + hits well -> genuine benefit confirmed. Effort S-M. Files: cli/memory_cmd.py, a new recall-stats command, .gitignore (the log is runtime).
- MOVE 2 — MULTI-SPACE ABLATION HARNESS (keep the complexity only if it earns lift). Problem: 7-space scoring = zero lift at 44 nodes. Build a repeatable ablation comparing single-space (default only) vs multi-space (variance-weighted) on a LABELED query set (query -> expected memory) using recall@k / MRR / nDCG — reuse/extend `memoryschema eval` with a space-mode toggle. Seed the ~20-30-pair gold set from the Move-1 recall log (synergy). Trigger: re-run at corpus-size milestones (100 / 250 / 500 entities) or on demand. Decision rule (pre-committed BEFORE seeing results, to resist sunk-cost): keep multi-space ACTIVE only when lift crosses a threshold (e.g. MRR delta >= 0.02 or +1 hit at recall@5) at the current size; below that keep dormant/flagged; if it never helps by a large corpus, REMOVE the per-space arrays + combiner to simplify. Effort M. Files: scripts/ablation_multispace.py (or extend eval_cmd) + a gold-set fixture.
- MOVE 3 (do last) — RE-JUSTIFY NEO4J vs JSONL+EMBEDDINGS. Problem: Neo4j is over-provisioned at 44 nodes; its cost (a container that must stay up + the preflight/reconcile reliability machinery) may exceed its benefit until scale. Benchmark retrieval QUALITY + LATENCY of Neo4j-backed vs JSONL-backed recall on the same gold set + corpus (reuse the Move-2 harness). Decision options: (a) keep Neo4j (justified if graph features / scale imminent); (b) make JSONL+embeddings the DEFAULT with Neo4j opt-in above a corpus-size threshold (simpler ops, no container to keep up); (c) document a size threshold to switch. Trade to weigh: Neo4j buys graph traversal (relation cascade), a native vector index (fast at large N), O(1) upsert, clean supersession; JSONL does status-filter + BM25/cosine fine at small N but degrades at large N — so the call is fundamentally size-gated. Most consequential + riskiest (Neo4j is woven through recall/migration/preflight) — hence LAST, after #1 gives usage data and #2 gives the harness. Output: a docs/ADR with the benchmark + the decision. Effort M-L.
- GUARDRAILS: do not add complexity to justify complexity — each move is small + reversible; pre-commit the keep/drop thresholds before seeing results (avoid rationalizing sunk cost); the moves are measurement/decision work, not speculative refactors. Sequencing 1->2->3 because Move 1's recall log seeds Move 2's gold set, and Moves 2+3 share the eval harness. Net goal: replace the 80/20 judgment call with data on whether each sophisticated layer earns its keep at the corpus's actual (and growing) size.

## Reasoning

The evaluation ([[memory-module-value-evaluation]]) found the module net-genuine but ~80/20, with the sophistication unproven at 44 nodes. Rather than rip out or double down on the fancy layers on a hunch, the plan turns each open question into a cheap measurement: usage (is it even read?), then per-layer payoff (multi-space lift, Neo4j-vs-JSONL) gated on corpus size. Measurement-first is the correct order because the biggest unknown (cross-session read usage) is also the cheapest to instrument and the one that, if it comes back negative, would make the other two moot.

## Notes

Three measurement moves (sequenced 1-&gt;2-&gt;3) to make the memory module's benefit measured rather than assumed. Driven by [[memory-module-value-evaluation]].

Migrated from helios 2026-07-13 (extraction seeding).
