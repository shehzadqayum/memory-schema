# Phase 0 — Reconnaissance Findings

> **HISTORICAL** — a point-in-time reconnaissance snapshot (June 2026, pre-v5). Several
> findings were later changed by design (e.g. embedding now runs BEFORE the gate).
> Current behavior: [`harness-manual.md`](../harness-manual.md).

All 7 assumptions confirmed. No §A fallbacks triggered.

## 0.1 — Observation storage shape: CONFIRMED
- JSONL: plain string list. Dedup via `set()` in `_upsert_inner` (store.py:235-242)
- Neo4j: string-list property `observations` + concatenated `observations_text` (neo4j_store.py:81-102)

## 0.2 — Embedding timing: CONFIRMED (A2 triggered)
- Gate runs BEFORE embedding in both CLI (memory_cmd.py:197→237) and hook (lines 64→74)
- The stage-4 consistency probe reads `memory.get('embedding')` — which is absent at gate time
- Probe is effectively dead code unless embedding is pre-computed elsewhere
- **Implication for Phase 4.1:** pre-gate embed refactor IS needed per plan §4.1

## 0.3 — SUPERSEDES trust guard: CONFIRMED (single choke point per backend)
- JSONL: pre-validation in `_upsert_inner` (store.py:163-192), raises ValueError
- Neo4j: inline in upsert relation loop (neo4j_store.py:130-160), raises ValueError
- Both use TRUST_LEVELS from config.py. Verification guard will be placed immediately after.

## 0.4 — Hook env inheritance: CONFIRMED
- `#!/bin/bash` + embedded `python3 -c` subprocess
- Inherits parent environment; reads `os.environ.get('VOYAGE_API_KEY')` (line 75)
- MEMORY_GENERATOR env var will be readable without modification

## 0.5 — Reflect cluster contents: CONFIRMED (full entity dicts)
- `store.list_all()` fetches all entries upfront (consolidation.py:223)
- `_cluster_by_associations()` returns lists of full dicts (line 128)
- Relations are available in cluster members — no additional fetch needed for Phase 5

## 0.6 — Recall rendering: CONFIRMED (two paths)
- Text output: CLI renders `[UNTRUSTED — ingested, provenance unverified]` (memory_cmd.py:88-94)
- JSON output: dumps raw dict, NO untrusted marker (memory_cmd.py:81-82)
- Staleness annotation (Phase 2.3) must be applied at BOTH paths

## 0.7 — Neo4j observations_text: CONFIRMED (preferred model viable)
- `observations_text` is a separate concatenated string property (neo4j_store.py:87,98)
- Fulltext index queries `observations_text`, NOT the `observations` list directly
- `observations_text` stripped from client results (line 712)
- **Implication for Phase 1.3:** PREFERRED model (JSON-per-element) is viable
  - `observations` list can carry JSON-encoded labelled elements
  - Text matching uses `observations_text` which will remain plain text
  - Must update `observations_text` construction to extract text from JSON elements
