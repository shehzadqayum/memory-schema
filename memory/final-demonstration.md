---
schema: 5
importance: 6
status: archived
---

Final system demonstration: 12 components verified, 108 entries, content-agnostic, all operational

## Observations

- Parse: XML → all fields including confidence and chain extracted correctly
- Confidence: conf=9, conf=2, none all score 0.6600 — confirmed metadata only, not scored
- V12: confidence=50 correctly rejected (out of range)
- L0 at 2017/2000 tokens — over budget, next write will trigger eviction
- 108 entries, 109 files, 15 MB store, 12 active chains, 11 superseded

## Reasoning

All 12 components demonstrated operational: parse, authorisation, gate, confidence (metadata only), recall, relations, backlinks, embedding spaces, variance-weighted combiner, supersedes, storage layers, validation. The system is architecturally complete and content-agnostic.

## Prompt

Demonstrate the memory system

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
