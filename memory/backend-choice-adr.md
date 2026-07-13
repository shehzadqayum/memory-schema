---
schema: 5
importance: 6
relations:
  - USES plan-memory-value-measurement
---

At 72 entities JSONL beats Neo4j on quality AND ~3x latency; Neo4j-default is a scale bet not yet paid

## Observations

- eval --mode backends (2026-07-12, 24 gold queries, 72 entities): JSONL recall@5 0.792 / mrr 0.668 / ndcg 0.709, median 513ms p90 758ms; Neo4j recall@5 0.750 / mrr 0.660 / ndcg 0.687, median 1678ms p90 2162ms
- Pre-committed rule (keep Neo4j default iff quality >= JSONL AND p90 < 500ms) FAILS: Neo4j is worse on all 4 quality metrics and ~3x slower
- Decision: DOCUMENT only, do not flip the production default (Neo4j is woven through recall/migration/preflight/'deps up' invariant — an operator ops call). Neo4j's value (graph traversal, native vector index at large N, O(1) upsert, clean supersession) is a SCALE bet; re-benchmark at 250/500 where its vector index should start winning

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
