---
schema: 5
importance: 6
status: archived
---

Full system demonstration: all components operational — 96 entries, 7 spaces, content-agnostic

## Observations

- Store: 96 entries (83 active, 13 superseded), 4 types: semantic 32, episodic 24, knowledge 19, procedural 8
- Confidence scoring: conf=9 → 0.594, conf=3 → 0.198, none → 0.660 (neutral) — working correctly
- Gate: 4 stages — ACCEPT for valid, REJECT for missing name — demonstrated
- Recall: chain-why-equal-weight-fails at 0.708 for "why does multi-space averaging fail"
- Parser: type="demo", confidence=8, chain field — all extracted from XML correctly
- L0 MEMORY.md: 53 entries, 1991/2000 tokens — near budget limit
- Relations: 4 USES from chain entity, 2 backlinks from evidence to chain — bidirectional working

## Reasoning

Every component demonstrated working end-to-end: store, spaces, authorisation, gate, confidence scoring, recall, relations, backlinks, supersedes, parser, and all storage layers. The system is architecturally complete and content-agnostic.

## Prompt

Demonstrate the memory system

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
