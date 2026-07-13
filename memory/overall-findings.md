---
schema: 5
importance: 9
status: archived
---

10 key findings: equal-weight fails, variance combiner works, 1:1 mapping, trust was complexity, confidence not scored

## Observations

- Equal-weight multi-space averaging monotonically degrades retrieval: single 0.608 → 3-space 0.601 → 4-space 0.557 → 5-space 0.555
- Variance-weighted combiner (divergence from default = weight) is self-regulating — no configuration needed
- 1:1 field-to-space mapping is cleanest: description most discriminative (0.35-0.47 gap), prompt most divergent (0.40 avg)
- 3 trust systems (provenance+basis+source) were overlapping complexity — removal simplified gate 6→4, eliminated Observation subclass
- Confidence must not score — calibration confound: scoring alters the outcomes used to evaluate confidence accuracy
- Chain entities work: ordered reasoning in observations, USES to evidence, backlinks for reverse access (2 hops)
- Immutability with single writable chain prevents unbounded accumulation (148-observation anti-pattern proved the need)
- Free-form type produced 4 organic types: knowledge 36, semantic 32, episodic 24, procedural 8
- Documentation must track implementation not prescribe — 3 remedial passes needed for alignment
- Pattern: additive complexity (spaces, combiner, chains) then subtractive simplification (trust removal) = more capability, less machinery

## Reasoning

The session evolved the system from 1 space with 3 trust mechanisms to 7 spaces with zero trust mechanisms. The key insight was that equal-weight averaging was the bottleneck, not the spaces — and that trust was overlapping complexity that could be replaced by a single non-scoring metadata field. The architecture is now content-agnostic, self-regulating (variance combiner), and immutable by default (authorisation states).

## Prompt

What are our findings overall?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
