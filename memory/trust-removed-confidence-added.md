---
schema: 5
importance: 9
status: archived
---

All trust mechanisms removed, replaced with confidence (1-10) — content-agnostic architecture

## Observations

- Removed: Observation(str) subclass, VALID_BASES, VERIFICATION_RANKS, V14, Q9, basis factor, verification guard, verified_at, basis upgrade, measured checks, inferred labeling
- Observations are now plain strings — no per-observation metadata
- Added: confidence attribute (integer 1-10), scored as confidence/10 multiplier
- SUPERSEDES retains cycle detection (R7) but no verification guard — any memory can supersede any other
- 627 tests passing after removal of 42 trust-related tests
- Architecture is now content-agnostic: no content inspection, no trust labels, author declares confidence

## Reasoning

The basis system (measured/inferred/reported) inspected content to determine trust — the opposite of content agnosticism. The confidence field lets the author declare their own confidence level (1-10) without the system judging the content. This is simpler, consistent with how importance works, and eliminates the complex Observation subclass machinery.

## Prompt

Remove all trust mechanisms and redesign using confidence scoring

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
