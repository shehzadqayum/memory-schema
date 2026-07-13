---
schema: 5
importance: 8
status: archived
---

Complete memory system after provenance removal: 13 LLM fields, 7 spaces, 4-stage gate, basis-based trust

## Observations

- 13 LLM-authored fields: schema, name, description (required) + type, importance, observations, prompt, reasoning, chain, relations, source, project, body
- 10 system-managed fields: status, embedding, embeddings, divergence_profile, created_at, last_accessed, access_count, verified_at, backlinks, associations
- 7 embedding spaces: default + name + description + observations + prompt + reasoning + chain (7168 max dims)
- 4-stage gate: validation, consistency, numeric probe, L0 echo (provenance stages removed)
- Trust via basis attribute on observations (measured/inferred/reported) — per-observation, epistemological
- Variance-weighted combiner: Σ(sim × divergence) / Σ(divergence) — no base weights, no heuristics
- Authorised/unauthorised states: only active chain writable, everything else read-only
- 90 entries, 78 active, 669 tests

## Reasoning

With provenance removed, the system is cleaner: trust is handled per-observation via basis (epistemological), not per-entity via declared labels. The gate pipeline dropped from 6 to 4 stages. The scoring formula lost the trust multiplier but retained the basis factor. The 7-space architecture and variance-weighted combiner are unchanged.

## Prompt

Explain how the memory system works now — show all the fields

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
