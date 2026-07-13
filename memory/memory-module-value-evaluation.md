---
schema: 5
importance: 7
relations:
  - INFORMS seven-space-scoring-activated
  - INFORMS memory-schema-reliability-hardened
  - USES plan-memory-value-measurement
---

Evidence-based verdict (2026-06-30) on whether the memory-schema module gives GENUINE vs assumed benefit…

## Summary

Evidence-based verdict (2026-06-30) on whether the memory-schema module gives GENUINE vs assumed benefit: net-genuine but ~80/20 — a small proven core (readable .md + semantic recall + supersession) wrapped in scale-bets (multi-space, access-decay, Neo4j graph) that are dormant/unproven at 44 nodes.

## Observations

- GENUINE, proven live: semantic recall beats keyword/BM25 on VOCAB-MISMATCH queries. Test: 'how much money can I afford to lose before getting kicked out of the challenge' (shares NO words with the target) ranked account-rdd-waterline #1 by embeddings vs #4 (buried under chain noise) by keyword. Second paraphrase: semantic #1 vs keyword #2. When query and memory SHARE vocabulary, keyword ties semantic — so the embedding value is specifically for paraphrased/conceptual queries, which is exactly how an LLM queries memory.
- GENUINE, proven live: (a) the markdown-as-truth layer — memory is readable, git-versioned, diffable, recoverable .md files (DB is a rebuildable projection); this is the biggest real benefit and it is essentially 'just files', not the database machinery. (b) Supersession: superseded notes are excluded from default recall and their successors surface instead (verified: 'latent bugs not yet fixed' returns memory-schema-bugs-fixed, not the superseded known-bugs).
- ASSUMED / inert at the current 44-node scale: (a) the 7-space multi-space scoring shows ZERO measured lift — single-space returns identical top results (small, topically-distinct corpus = low inter-space divergence); right design, wrong scale, not broken. (b) access_count tracking is INERT: 0 of 44 entities have EVER been accessed (recall is read-only and records nothing), so the procedural 'boost frequently-used memories' scoring has no data to act on. (c) The Neo4j graph (a container that must stay up + the reliability machinery to keep it healthy) is over-provisioned vs a flat JSONL store + embeddings + a status flag at this size. (d) The 482 k-NN association edges and the variance-weighted combiner are unmeasured vs plain cosine + a status filter.
- KEY RISK (not disproven): the classic memory-system failure mode is 'write a lot, read little'. access_count=0 means cross-session READ is currently UNMEASURED — the central value claim ('memory helps the next session') is plausible but faith-based until recall usage is logged. Measuring retrieval is also only a first-order proxy; true utility (did the recalled memory change the answer?) needs response-attribution.
- BOTTOM LINE: not purely fancy-assumed (semantic recall + supersession are real, demonstrated wins over the naive alternatives of no-memory or grep-a-file), but a fair chunk of the sophistication is currently assumed. You could reproduce ~80% of today's value with 'markdown files + a vector index + a status field' (a local, file-first mem0-lite). The graph DB / multi-space / access-decay / associations are bets on a future corpus of thousands with heavily-exercised recall — justified later, not yet earning their keep. Remediation = [[plan-memory-value-measurement]] (measure usage, ablate multi-space at scale, re-justify Neo4j).

## Reasoning

Run deliberately as a skeptic's test. The discriminating method was a FAIR vocabulary-mismatch recall query (the first informal test used a query whose words were already in the target, so keyword tied — not a real test). The same probing surfaced both the genuine win (embeddings rank the right memory #1 when words do not match) and the dormant machinery (multi-space zero-lift, access_count 0/44, Neo4j over-provisioned). The honest 80/20 framing matters because this session spent ~15 commits hardening the module — robustness is real engineering quality, but it is insurance on an asset whose day-to-day payoff today is a readable notebook + good semantic search.

## Notes

Evidence-based evaluation of the memory module's real benefit. Remediation plan: [[plan-memory-value-measurement]]. Relates to [[seven-space-scoring-activated]] (the zero-lift finding) and [[memory-schema-reliability-hardened]] (the hardening whose cost this weighs).

Migrated from helios 2026-07-13 (extraction seeding).
