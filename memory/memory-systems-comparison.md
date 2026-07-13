---
schema: 5
importance: 7
status: archived
---

How this system compares: standard RAG core + novel multi-space/variance/chains/immutability on top

## Observations

- Standard: vector embedding, cosine similarity, recency+importance scoring — everyone does this
- Novel: 7 independent spaces per entry (most use 1), variance-weighted combiner (most use fixed/equal), divergence profiles as structural fingerprints
- Novel: chain entities with ordered reasoning + USES relations + bidirectional traversal — closer to knowledge graph than flat RAG
- Novel: authorised/unauthorised immutability, content-agnostic trust (confidence metadata-only)
- Missing vs production: no auto-chunking, no reranker in hot path, no context window budget for injection, behavioral enforcement only
- Fundamental pattern is still RAG: store externally, retrieve at query time, inject into context

## Reasoning

The core is standard RAG. The differentiation is in the multi-space architecture (7 spaces with variance weighting), the graph structure (typed relations with cascade), and the operational model (immutability, chains, content-agnostic). These are engineering choices on top of the RAG pattern, not a fundamentally different approach. The alternative (fine-tuning) isn't practical for real-time memory.

## Prompt

Is this how memory systems work?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
