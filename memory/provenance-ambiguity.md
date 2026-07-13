---
schema: 5
importance: 8
status: archived
---

Provenance introduces trust ambiguity — self-declared labels, effectively binary, basis attribute is the better mechanism

## Observations

- Provenance is self-declared — LLM labels its own content as first-party trust 3, no verification
- 3 of 4 provenance values map to the same trust level (3) — the hierarchy is effectively binary (trusted vs ingested)
- Nothing prevents setting provenance="user" on LLM-generated content — the declaration is unverifiable
- The basis attribute on observations (measured/inferred/reported) is per-observation and epistemological — better trust mechanism
- basis describes HOW a fact was established, provenance describes WHO wrote the entity — basis is more meaningful
- Provenance enforcement (L0 gating, SUPERSEDES guards) only matters for ingested content — could be a boolean flag

## Reasoning

The provenance system creates a false sense of trust granularity. Three values (first-party, user, derived) are treated identically at trust level 3. The only meaningful distinction is ingested (external, untrusted). The basis attribute already provides per-observation trust that is epistemologically grounded (measured vs inferred vs reported). Provenance is a blunt instrument where basis is precise.

## Prompt

Provenance introduces ambiguity — trust levels ambiguity — into the framework

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
