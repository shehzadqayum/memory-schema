---
schema: 5
importance: 7
---

Evaluation: provenance and source overlap — provenance is overloaded (binary trust), source is underused

## Observations

- provenance: categorical trust (first-party/user/derived/ingested) — drives scoring, L0 gating, SUPERSEDES
- source: free text attribution (session hash, URL, path) — only required for ingested (V13)
- Trust hierarchy is effectively binary: trusted (3) vs ingested (1) — 4 values create illusion of granularity
- source is rarely set on non-ingested memories — could be valuable as general provenance trail
- Most memories are first-party with no source — both fields contribute nothing in the common case
- If redesigning: one free-form provenance field, trust inferred from content not declared labels

## Reasoning

The two fields exist because trust and attribution are conceptually different (how much to trust vs where it came from). In practice, provenance carries all enforcement power while source is metadata. The 4-value provenance is effectively binary (trusted vs ingested). A cleaner design would use source more actively (record session context on every write) and simplify provenance to two values.

## Prompt

Evaluate the use of both source and provenance

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
