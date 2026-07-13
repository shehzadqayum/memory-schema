---
schema: 5
importance: 8
relations:
  - USES plan-memory-value-measurement
---

Attribution join = guardrail NOT loss fn; tune via paired replay vs curated gold; suppression is censored

## Observations

- 53 epistemic params, 9 TOML-exposed, 9 high-suppression-risk (recall_seed_count=3 hardcoded, l0_echo_threshold no TOML key, embedding_input_max_chars hardcoded)
- Attribution is censored implicit feedback: citations only observable for SERVED memories - knowledge suppression lives in the zero-propensity region; never optimize theta against it (Joachims 2017, Chaney 2018)
- Between-cell attribution A/B needs ~710 recalls per 10pp effect; helios log has 123 recalls/34 citations - use paired within-query replay (same logged queries, theta vs theta-prime, McNemar) instead
- Suppression pipeline exists today: recall log caps hits at 10 -> dream never_surfaced computed from log -> rank-11+ memory becomes archival candidate
- recency_decay (0.995/hr score) vs recall_decay (0.8 BFS hop) are distinct; LOWERING recency_decay tightens (0.95^720h~1e-16)

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
