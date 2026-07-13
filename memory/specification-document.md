---
schema: 5
importance: 8
status: archived
---

Full memory system specification document generated at docs/memory-system-specification.md — 14 sections

## Observations

- 14 sections: overview, entity schema, write pipeline, retrieval, spaces, relations, chains, auth, storage, validation, recall, audit, CLI, principles
- Covers all 22 fields (13 LLM + 9 system), 7 spaces, 4-stage gate, variance-weighted combiner, chain lifecycle
- Includes the 7 design principles: content-agnostic, 1:1 mapping, variance-weighted, immutable default, graceful degradation, confidence for calibration, recall before respond
- Based on recalled memories: complete-schematic (0.732), architecture-schematic (0.729)

## Reasoning

The specification consolidates all architectural decisions, pipeline details, and design principles into a single reference document. It was generated after recalling the schematic and architecture memories, ensuring consistency with the established system description.

## Prompt

Generate a full memory specification description document

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
