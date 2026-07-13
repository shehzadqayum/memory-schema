---
schema: 5
importance: 8
status: archived
---

Complete memory system: 13 LLM fields, 9 system fields, 7 spaces, 4-stage gate, content-agnostic

## Observations

- 3 required fields (schema, name, description) + 10 optional LLM fields + 9 system-managed fields
- 7 embedding spaces: 1:1 field mapping (name, description, observations, prompt, reasoning, chain) + default blend
- Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no heuristics
- 4-stage gate: validation, consistency, numeric probe, L0 echo
- Scoring: recency × w_r + importance × w_i + relevance × w_v, then × confidence/10
- Authorised/unauthorised states: only active chain writable
- Content-agnostic: no trust labels, no provenance, no basis — author declares importance and confidence
- 95 entries, 83 active, 627 tests

## Reasoning

The system is architecturally complete and content-agnostic. Every entity field maps to an embedding space. The variance-weighted combiner handles scoring automatically from precomputed divergence profiles. Confidence replaces all trust mechanisms as a simple author-declared value.

## Prompt

Describe the current memory system including all its fields

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
