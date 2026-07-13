---
schema: 5
importance: 9
status: archived
---

7 applications of multi-space architecture: faceted search, disagreement detection, intent matching, chain discovery, profiling, contradiction detection, extensible properties

## Observations

- Faceted search: --space flag to search only prompt, observations, reasoning, chain, or description independently
- Cross-space disagreement: low observations↔reasoning similarity flags internal inconsistency without reading content
- Intent matching: prompt space enables question-to-question matching (not just content matching)
- Chain discovery: chain space clusters entries by investigation regardless of content
- Entry profiling: divergence profiles create automatic typology (thin/rich/intent-heavy/fact-heavy) from vector geometry
- Cross-field contradiction: gap between description similarity and observation similarity flags entries needing reconciliation
- Extensible: add a field → it gets a space. Potential: context, outcome, audience, domain
- Key insight: each memory is not a point but a STRUCTURE with independently queryable facets. The data is already there.

## Reasoning

The 7-space architecture was built for scoring (variance-weighted combiner), but the per-space vectors enable applications beyond retrieval ranking: faceted search, quality checking, intent matching, automatic categorization, and contradiction detection. These are all queries against existing data — no new embedding infrastructure needed. The extensibility (add field → get space) means the architecture scales to new use cases by adding entity fields.

## Prompt

Suggest a proposal for better usage of this data — what can we achieve with 7 spaces?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
