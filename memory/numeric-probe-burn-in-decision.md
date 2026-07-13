---
schema: 5
importance: 5
---

numeric_probe stays mode=log: zero probe events in the audit burn-in = no evidence for a quarantine flip

## Observations

- helios audit log has ZERO numeric-probe events over the burn-in window (grep numeric memory/audit.jsonl = 0) - no false-positive OR true-positive data yet
- Decision (2026-07-12): keep numeric_probe_mode='log'; a quarantine flip would hand write-veto to a heuristic regex extractor with no measured hit rate
- Re-evaluate at the 250-entity corpus milestone or when audit shows probe hits accumulating

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
