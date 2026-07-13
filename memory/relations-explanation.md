---
schema: 5
importance: 7
status: archived
---

7 relation types: USES, MODIFIES, SUPERSEDES, DEPENDS_ON, INFORMS, CONTRADICTS, MITIGATES

## Observations

- 4 informational (USES, MODIFIES, DEPENDS_ON, INFORMS) — create links, no side effects
- SUPERSEDES: marks target superseded, trust+verification guards, cycle detection, force record
- CONTRADICTS: symmetric — auto-creates reverse edge on target, logs force record
- MITIGATES: target stays active but gets 0.95 score dampening
- Relations create forward links, backlinks are computed as reverse. Both traversed in recall cascade.
- Hub bonus: +0.05 × ln(1 + backlinks) — more connected memories score higher
- Chain entities use USES to link to evidence — backlinks enable reverse traversal from evidence to chain

## Reasoning

Relations are the graph structure of the memory system. Most are informational links that enable cascade traversal. SUPERSEDES, CONTRADICTS, and MITIGATES have side effects that alter scoring or status. The USES relation is the most important for chains — it creates the bidirectional link between chain entities and their evidence.

## Prompt

Explain relations

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
