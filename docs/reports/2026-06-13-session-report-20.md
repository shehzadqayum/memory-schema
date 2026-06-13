# Session Report — 2026-06-13 (Session 20)

## Summary

6 commits, 10 files changed (+725/-48 lines), 612 tests passing. Phase M1 — field spaces gating experiment (NO SHIP).

## Commits

| Hash | Tag | Description |
|------|-----|-------------|
| `341ae4c` | [S1] | Phase M1 — field spaces: observations vs reasoning |
| `950a482` | [S2] | M1.1 — field spaces for observations and reasoning |
| `aadfe03` | [S2] | M1.2 — multi-space storage and scoring |
| `25a1340` | [S2] | M1.3 — per-space reembedding with --space option |
| `321229e` | [S2] | M1.4 — experiment combiner: equal weighting, no query classification |
| `234adbf` | [S2] | M1.5 — field-space gating experiment: NO SHIP |

## Audit

| # | Item | Evidence | Result |
|---|------|----------|--------|
| 1 | M1.1: Field spaces in embedding_input.py + registry | Tested (23 tests) | PASS |
| 2 | M1.2: Multi-space storage + scoring in store.py | Tested (11 tests) | PASS |
| 3 | M1.3: Per-space reembedding with --space CLI option | Tested (5 tests) | PASS |
| 4 | M1.4: Equal-weight combiner (EXPERIMENT_WEIGHTS=None) | Tested (4 tests) | PASS |
| 5 | M1.5: Gating experiment ran, numbers recorded, decision made | Measured (NO SHIP) | PASS |

## Experiment Results

| Metric | No embedding | Single-space | Multi-space |
|--------|-------------|-------------|-------------|
| recall@5 | 0.458 | 0.622 | 0.622 |
| nDCG@10 | 0.476 | 0.608 | 0.601 |
| MRR | 0.611 | 0.778 | 0.778 |

**Decision:** Multi-space (nDCG 0.601) does not beat single-space (nDCG 0.608). NO SHIP to default scoring. Infrastructure remains opt-in.

## Residuals

- Hook integration test: E2 write path Tested but not Operative via subprocess (source: session 18, deferred — out of M1 scope)

## Current State

- **Branch:** main
- **Latest commit:** `234adbf`
- **Tests:** 612 passing across 34 test files
- **Schema:** v4
- **Single-space baseline:** recall@5=0.622, nDCG@10=0.608 (with embeddings)
- **Pending work:** M2 (summary/prompt spaces — gated, higher bar), M3 (mutable/drift — deferred)
