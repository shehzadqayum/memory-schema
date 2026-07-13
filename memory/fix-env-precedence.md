---
schema: 5
importance: 10
status: archived
---

Plan to fix env var precedence inversion, redundant import, and add hierarchy integration tests

## Observations

- from_toml() passes TOML values as explicit kwargs — bypasses default_factory env var reads
- Fix: overlay env vars via setattr after instance construction
- store.py:283 has redundant inline import already at module level
- No integration tests for search/recall with mixed-project entities

## Reasoning

The env var precedence inversion is a real bug — TOML silently overrides env vars. The docstring claims the opposite. This was introduced when Fix 7 removed env var reads from resolve_config_chain without compensating in from_toml().

## Prompt

plan fix for env var precedence, redundant import, integration tests

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-2-close.
