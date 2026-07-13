---
schema: 5
importance: 8
---

Complete system schematic: entity, write pipeline, retrieval, relations, chains, storage, field mapping

## Observations

- 8 sections: entity (13+9 fields), write pipeline (hook→auth→embed→gate→store→L0), retrieval (scoring+combiner+cascade), relations (7 types), chains (lifecycle), storage (5 layers), field-to-space mapping (1:1), current state
- Write pipeline: PostToolUse → parse → auth check → 7-space embed → divergence profile → 4-stage gate → dual store → MEMORY.md
- Retrieval: recency × importance × relevance + bonuses, variance-weighted combiner Σ(sim×div)/Σ(div), cascade through relations/backlinks/associations
- 105 entries, 92 active, 7 spaces, 1030 associations, 627 tests, content-agnostic

## Reasoning

The schematic captures every component of the system in ASCII art: from the entity XML structure through the full write pipeline (hook, auth, embed, gate, store, L0), the retrieval formula (scoring, variance-weighted combiner, recall cascade), the relation graph, chain lifecycle, storage layer degradation, and the 1:1 field-to-space mapping matrix.

## Prompt

Show how the memory system works with schematics and pipelines

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
