---
schema: 5
type: episodic
importance: 2
status: archived
---

Confirmed multi-space embedding is now the default hook behavior

## Observations

- Every hook write produces 3 embedding spaces (default, observations, reasoning) with 1024 dims each
- No flag or configuration needed — it is the default behavior in hook-post-write.sh

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
