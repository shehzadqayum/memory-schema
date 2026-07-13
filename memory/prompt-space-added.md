---
schema: 5
importance: 5
status: archived
---

Added prompt embedding space — 5 spaces now active (5120 max dims per entry)

## Observations

- Prompt space isolates the user input that triggered the memory — captures intent separately from response
- 36/58 entries have prompt text (62% coverage), 22 skipped as structural absence
- Previously prompt was only in reasoning space (combined with reasoning text) — now also available standalone
- 5 spaces: default (all fields), observations (facts), reasoning (rationale+prompt), description (summary), prompt (user input)

## Reasoning

Earlier evaluation recommended skipping prompt space due to short text (avg 43 chars) and redundancy with reasoning space. User overrode this — having the raw user intent as a separate vector enables intent-based retrieval independent of the system response.

## Prompt

User requested adding prompt as a separate embedding space

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
