---
schema: 5
importance: 8
status: archived
---

Remedial Rev 2 evaluation: all critical/high closed, M1-M3 medium open, L1-L4 low open, 3 confirms ratified

## Observations

- All A1/B1-B4/C1-C4 verified as closed — trust/confidence model coherent
- M1: downgrade "embeddings separate working and corpus" to tendency — no enforcing mechanism
- M2: document backend-dependent ranking as accepted limitation (Neo4j +0.1 vs JSONL +0.3)
- M3: strike "computed from source signals" — importance is agent-assigned (content-agnostic)
- L1: schema="3" → "4" in implementation-guide fixture
- L2: test-count headline needs reconciling with breakdown
- L3: status in tech-ref — already fixed (server-managed fields added)
- L4: rename "SUPERSEDES Guards" → "SUPERSEDES Integrity" (only R7 remains)
- CONFIRM-1: importance double-duty accepted (retrieval weight + enforcement band)
- CONFIRM-2: corpus origin moot (working-memory-only deployment)
- CONFIRM-3: R2 closed relation set retained as structural exception

## Reasoning

The rev 2 report correctly identifies that all blocking defects are resolved. The remaining items are medium consistency (M1-M3), low wording (L1-L4), and design confirmations (CONFIRM 1-3). No item blocks use of the system. The three design confirmations align with the content-agnostic principle.

## Prompt

Evaluate remedial report rev 2

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
