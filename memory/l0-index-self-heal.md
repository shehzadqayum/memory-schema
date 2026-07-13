---
schema: 5
importance: 7
relations:
  - USES reconcile-malformed-guard
  - USES memory-schema-reliability-hardened
---

MEMORY.md (L0) is now REGENERATED from the store's active set on every write and on reconcile…

## Summary

MEMORY.md (L0) is now REGENERATED from the store's active set on every write and on reconcile — not appended; don't hand-edit it, run reconcile to heal

## Observations

- Commit aec4a38 (2026-07-01, VENDORED packages/memory-schema): MEMORY.md is a FULL regenerate of the store's ACTIVE entries, not an append-only list. l0_budget.rebuild_index(index_path, entries|store_path, budget) rebuilds it status-filtered (superseded/archived/quarantined excluded), grouped by type (Knowledge/Procedures/Session History), ranked by importance (store-agnostic — no JSONL-only _score_entry), and budget-capped with a non-silent "N dropped for the L0 budget" note.
- The drift it fixed: the old hook APPENDED one line per write and the budget only EVICTED, and neither filtered by status — so MEMORY.md kept 8 superseded/archived entries while missing 14 ACTIVE ones (including importance-8/7 memories and both session chains); it showed 34 entries while the store held 40 active. reconcile synced .md/JSONL/Neo4j but never touched MEMORY.md, so there was no self-heal path.
- Two heal paths, proven byte-identical (same set AND order): the write HOOK rebuilds from the SAME store it wrote to (Neo4j when up, else JSONL) so the just-written memory shows even though store.jsonl can lag Neo4j; `memoryschema reconcile` step 7 rebuilds from the authoritative JSONL — the guaranteed heal that makes all FOUR layers agree (.md / JSONL / Neo4j / MEMORY.md).
- OPERATIONAL consequence: do NOT hand-edit MEMORY.md expecting it to stick — the next memory write or reconcile regenerates it from the store. To change what L0 shows, change the store (add/supersede/adjust importance of an entity) then let the hook/reconcile rebuild. The L0 budget is config.l0_token_budget (default + toml now 3000); only the lowest-importance ACTIVE entries drop when over, and the drop is reported.
- Regression-locked in tests/test_l0_rebuild.py (6 tests): active-only, grouped, importance-ranked, budget-drops-lowest, idempotent, store-path load. Full suite green.

## Reasoning

This is the L0 sibling of the reconcile malformed-guard: both replace a fragile, drift-prone mechanism with one that regenerates from the source of truth. The core insight is the same as the malformed-guard's — an index maintained by incremental append (or by discipline) inevitably drifts; regenerating it from the authoritative store on every change makes drift structurally impossible. Ranking by importance rather than the JSONL _score_entry keeps rebuild_index decoupled from the scoring internals so it works identically on Neo4j or JSONL entries, which is why the hook (Neo4j) and reconcile (JSONL) paths produce the same index. Kept the token budget (L0 is always in context) but made eviction status-aware and never silent.

## Chain

chain-session-2026-06-30 — memory integrity: the L0 index self-heal

## Notes

Durable record of the L0 (MEMORY.md) self-heal (commit aec4a38). See [[chain-session-2026-06-30]] (Step 16) for the narrative and [[reconcile-malformed-guard]] for the sibling integrity fix.

Migrated from helios 2026-07-13 (extraction seeding).
