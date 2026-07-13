---
schema: 5
importance: 7
status: archived
---

Remedial Rev 2 fixes: M1-M3 medium + L1-L4 low all implemented, 627 tests passing

## Observations

- M1: embedding separation claim downgraded to tendency with no-enforcing-mechanism caveat
- M2: backend-dependent ranking documented as accepted limitation at schema.md L290
- M3: corpus importance "computed from source signals" → "set by importing agent"
- L1: schema="3" → "4" in implementation-guide test fixture
- L2: test count 569/33 → 627/34 + 2 integration in impl-guide + tech-ref
- L4: "SUPERSEDES Guards" → "SUPERSEDES Integrity" (only R7 cycle detection remains)
- All remedial items from both Rev 1 and Rev 2 now closed

## Reasoning

The medium items (M1-M3) were all correctness fixes: an unsupported claim, an undocumented divergence, and a contradictory definition. The low items (L1-L4) were mechanical. All six open items now closed. The remedial register is clear.

## Prompt

Implement M1-M3 and L1-L4 from remedial report rev 2

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
