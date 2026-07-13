---
schema: 5
importance: 7
relations:
  - USES memory-schema-reliability-hardened
---

reconcile aborts on a present-but-unparseable memory .md (corruption) instead of pruning its entity…

## Summary

reconcile aborts on a present-but-unparseable memory .md (corruption) instead of pruning its entity — validated by catching its own author's raw-ampersand on first live use

## Observations

- Commit e2ba450 (2026-07-01, VENDORED packages/memory-schema): reconcile._parse_md now returns (entities, malformed); a .md that contains a memory-entity tag but fails to parse is collected as malformed rather than dropped, and a NON-overridable guard (ahead of the empty/shrink guard) aborts reconcile — naming the files, pruning nothing, rewriting nothing — so a corrupt entity file can no longer be mistaken for an intentional deletion and silently pruned from JSONL+Neo4j. diff()/sync report malformed and force in_sync=False; the CLI prints a fix-it hint.
- Motivating incident (chain-session-2026-06-30 Step 11): a raw ampersand in a chain observation broke the strict XML parse, and the PRE-fix reconcile silently pruned the now-unparseable chain (node count 47 to 46), caught only by eyeballing the count. The guard makes that failure loud instead of silent.
- Empirical validation on the FIRST live use (Step 14 to 15): while writing the very commit that recorded the fix, a raw ampersand was AGAIN introduced — into the chain description this time — and reconcile ABORTED loudly naming the file instead of pruning it. The guard prevented the exact failure mode it was built for, triggered by the same author who kept making the mistake.
- Design lesson (generalizes): write-time discipline (XML-escape ampersand and angle-brackets, the documented M14 hazard) is NECESSARY but INSUFFICIENT — it failed twice (Steps 11, 14) even with the hazard documented in CLAUDE.md and freshly top-of-mind. A structural guard that refuses loudly is what actually protects integrity; prefer a structural refusal over relying on care. Sibling of the Tier-1 empty-md guard, at the per-entity grain.
- Regression-locked in tests/test_reconcile.py: malformed .md to abort + the entity PRESERVED (not pruned); diff reports it; a non-entity .md (notes/README) is NOT flagged (no false positive). Verified 9/9 reconcile tests + full suite green; live corpus reconciled clean.

## Reasoning

The value here is not just the mechanism but the empirical proof of a design philosophy: the guard was validated by its own author's recurrence of the exact bug, on the first live reconcile after it shipped. That is the strongest possible argument that integrity must be enforced structurally, not by discipline — the person most aware of the hazard, immediately after building the fix for it, still made it. Made the guard non-overridable (unlike --allow-empty) because a parse failure has one unambiguous resolution: fix the XML or delete the file; there is no legitimate "reconcile anyway". Keep this in mind for any future integrity mechanism: assume the operator (human or LLM) will make the mistake the docs warn against, and make the system refuse loudly rather than trust them not to.

## Chain

chain-session-2026-06-30 — memory integrity: the malformed-file reconcile guard

## Notes

Durable record of the reconcile malformed-file guard (commit e2ba450) and its first-use validation. See [[chain-session-2026-06-30]] (Steps 11-15) for the narrative and [[memory-schema-reliability-hardened]] for the broader reliability work.

Migrated from helios 2026-07-13 (extraction seeding).
