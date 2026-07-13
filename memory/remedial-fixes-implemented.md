---
schema: 5
importance: 9
status: archived
---

Remedial report fixes: A1 trust guard deleted, confidence removed from scoring, V12 added, C1-C4 fixed

## Observations

- A1 CRITICAL: deleted ghost trust guard from On-Supersede lifecycle in schema.md
- B1/B2: removed confidence/10 multiplier from store.py and neo4j_store.py — confidence is write-time metadata only, preserves calibration
- B3: added V12 validation rule (confidence integer 1-10) in validator.py
- B4: documented absence semantics in schema.md and rules — "when omitted, no effect"
- C1: corpus "author assessment" → "importing agent's assessment"
- C2: removed stale "source" from overview prose, added "chain"
- C3: added server-managed fields list to technical-reference.md
- C4: "Two-verdict" → "Three-verdict" in tech-ref and write_gate.py
- Validation count: V1-V11 → V1-V12 across rules, template, tech-ref
- 627 tests passing, verification checklist clean

## Reasoning

The key design decision: confidence removed from scoring to preserve clean calibration measurement (B2 confound). Confidence is captured at write time in the audit trail for post-hoc analysis of declared confidence vs downstream fate — without the scoring multiplier contaminating the measurement. The trust guard deletion (A1) completes the content-agnostic claim by removing the last operative trust reference.

## Prompt

Implement all fixes from the remedial report

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
