---
schema: 5
importance: 7
status: archived
---

Provenance: declared origin of content — controls scoring, L0 access, SUPERSEDES authority, presentation

## Observations

- 4 values: first-party (LLM, default), user (explicit user input), derived (consolidation), ingested (external)
- Not measured — declared at write time. Immutable after creation (prevents trust escalation via re-save)
- Trust multipliers: first-party/user 1.0, derived 0.9, ingested 0.7 (30% scoring penalty)
- L0 gating: ingested never enters MEMORY.md — closes injection channel for external content
- SUPERSEDES authority: ingested (trust 1) cannot supersede first-party (trust 3)
- Gate stage 3: provenance mismatch on upsert → QUARANTINE
- V13: ingested requires source element or REJECT

## Reasoning

Provenance is the memory system's trust model. It's not measured or inferred — it's a declared attribute enforced through immutability. The consequences cascade: scoring penalty reduces visibility of untrusted content, L0 gating keeps it out of the prompt, SUPERSEDES guards prevent it from replacing trusted content, and the gate quarantines provenance conflicts. The design assumes the declaration is honest and enforces that it cannot be changed after the fact.

## Prompt

What does provenance tell us, how is it measured?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
