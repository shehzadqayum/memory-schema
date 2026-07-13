---
schema: 5
importance: 8
status: archived
---

5 multi-space applications demonstrated on real data: faceted search, disagreement, intent matching, profiling, contradiction

## Observations

- Faceted search: prompt-space reranks results — bash-python-quoting-rule jumps from #3 to #1 for hook-related query
- Cross-field: session-2-close has obs↔rea similarity 0.234 (most divergent), chain-live-accumulation-design 0.881 (most aligned)
- Intent matching: "why remove trust?" matches stored prompt "Remove all trust mechanisms..." at 0.671 — question-to-question
- Profiling: 16 rich, 14 intent-heavy, 9 fact-heavy — categories from vector geometry, no labels
- Contradiction: 6 pairs with description sim > 0.6 but observation gap > 0.15 — same topic, different facts
- All applications run against existing data — no new infrastructure needed, just queries against 7-space vectors

## Reasoning

Each application demonstrates a capability that single-vector systems cannot provide. Faceted search differentiates intent from content. Cross-field analysis detects internal inconsistency. Intent matching finds prior questions. Profiling categorizes without labels. Contradiction detection finds update candidates. All from the same 7 vectors per entry.

## Prompt

Show examples of faceted search, cross-field analysis, intent matching, structural profiling, contradiction detection

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
