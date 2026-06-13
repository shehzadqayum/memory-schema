# Multi-Space Embedding: Enabling Phases + Registry

## Context

The multi-space embedding plan requires two enabling fixes before any space work begins. The eval harness cannot measure the real system (imports break on clean install, runs only against synthetic fixtures). The write path silently drops gate stages 4-6 (hook embeds after gate with no store/config; numeric probe and L0 echo are unreachable). Building spaces on unmeasurable, broken infrastructure reproduces the project's documented failure pattern: features built, unit-tested, marked complete, found unreachable.

## Prior Residuals (from [S4] 13d4836)

None.

## Exploration Findings

### Eval harness (E1 preconditions)
- eval_cmd.py imports `from tests.eval.fixtures/metrics` — tests/ not in package, breaks on clean install
- Salience mode shows synthetic baselines only; never connects to actual gate/audit data
- Retrieval mode runs against synthetic tempdir fixture store only; no --store path option

### Write path (E2 preconditions)
- **Hook (hook-post-write.sh:64):** calls `gate_check(memory)` with NO store, NO config. Stages 3-6 unreachable.
- **Hook (hook-post-write.sh:74-86):** embeds AFTER gate. Stage 4 consistency probe + stages 5-6 probes need embedding → dead code on hook path.
- **CLI write (memory_cmd.py:221):** calls `gate_pipeline(memory, store=store)` — has store but NO config. Embeds after gate.
- **MEMORY_GENERATOR:** never read by hook. generator_id is null on every write.
- **Ingest examples:** provenance not set (defaults to first-party, disabling L0 gating). Schema dict says 2, f-string says 4.

### Embedding input drift (M0 precondition)
- **Full (5 fields):** name+description+observations+prompt+reasoning — consolidation.py, reembed.py, hook
- **Partial (4 fields):** description+observations+prompt+reasoning — memory_cmd.py, hook_cmd.py (missing name)
- **Minimal (2 fields):** description+observations — ingest examples
- No canonical compose function in embeddings.py; callers duplicate logic

## Phase E1 — Make the eval harness measure the real system ✓ 27c4d32

### E1.1 Make tests.eval importable at runtime
- Move `tests/eval/fixtures.py` and `tests/eval/metrics.py` to `src/memoryschema/eval/` as a proper subpackage
- Update eval_cmd.py imports: `from memoryschema.eval.fixtures import ...`
- Update test_eval.py imports to use the new location
- Keep tests/eval/test_eval.py as the test file (tests stay in tests/)
- Verify: `pip install -e .` in clean venv, `memoryschema eval` runs without ImportError

### E1.2 Wire real data into eval modes
- **Retrieval mode:** add `--store PATH` option (default: configured store path). Load real store instead of synthetic tempdir.
- **Salience mode:** add `--audit PATH` option. Read `write_decline` and `gate_decision` records from audit.jsonl, build decision list, score against fixtures.

### E1.3 Produce baseline report
- Run retrieval eval against current real store (36 nodes indexed)
- Record recall@k, MRR, nDCG as the single-space baseline
- Store results in docs/eval/ or similar — this is the number every future space must beat

**Verification status required:** Operative (command runs on real data and emits numbers, not just "code written")

## Phase E2 — Make the write path trustworthy ✓ b5aaec4

### E2.1 Fix gate-before-embed ordering in hook
- In hook-post-write.sh: compute embedding BEFORE calling gate
- Call `gate_pipeline(memory, store=store, config=config)` instead of `gate_check(memory)` with no args
- Construct store and config in the hook's Python block
- Integration test: seed a numeric contradiction in the store, write a conflicting entry through the hook, assert quarantine fires

### E2.2 Fix CLI write path
- Pass config to gate_pipeline: `gate_pipeline(memory, store=store, config=config)`
- Embed BEFORE gate so stages 4-6 have a vector
- Verify: CLI write with seeded contradiction triggers quarantine

### E2.3 Wire generator stamp in hook
- Read `os.environ.get('MEMORY_GENERATOR')` in hook
- Set `memory['generator'] = generator_id` before upsert
- Verify: write with MEMORY_GENERATOR set, read stored record, confirm non-null generator

### E2.4 Fix ingest examples
- Set `provenance='ingested'` in ingest_tweets.py and ingest_forum.py
- Fix schema dict: `'schema': 2` → `'schema': 4`
- Verify: ingested entries have provenance='ingested' and are excluded from MEMORY.md by L0 gating

**Verification status required:** Operative (end-to-end hook test quarantines seeded contradiction; generator stamp non-null; ingested entries gated from L0)

## Phase M0 — Registry and combiner slots (behavior-neutral) ✓ 2e003d8

### M0.1 Canonical embedding input function
- Create `src/memoryschema/embedding_input.py` with single `compose_embedding_text(entry, space='default')` function
- Default space: name+description+observations+prompt+reasoning (the full canonical form)
- Replace all 6 drifting copies to call this function
- Verify: all tests pass, baseline unchanged

### M0.2 Space registry
- TOML-configurable registry in config.py: `[spaces.default]` with type=immutable, input=compose_embedding_text, embedder=voyage
- Registry resolves through TOML inheritance chain
- Populate with exactly one entry: `default` = today's system
- Verify: behavior unchanged, baseline unchanged

### M0.3 Combiner slot
- Function: `combine_similarities(per_space_sims: dict[str, float]) -> float`
- Default: identity (return `default` space sim only)
- Coverage-aware: iterates only present spaces, never reads absent as zero
- Verify: all tests pass, eval baseline identical to E1.3

**Verification status required:** Tested + Operative (tests pass AND eval baseline unchanged)

## Phase R1 — Resolve residuals: real-data query set + hook test

### R1.1 Real-data query set
The eval fixture queries reference synthetic entities (knowledge-0, session-event-0, etc.) that don't exist in the real store. The real store has 36 entities: session-close memories, plans, and project memories. Build a query set matched to real content:
- 4-6 queries with relevant entity lists drawn from actual stored names
- Cover: session history recall, plan recall, project fact recall, cross-session search
- Run `memoryschema eval --store memory/store.jsonl` and record the real baseline

### R1.2 Hook integration test
Write a test that exercises the hook's Python block end-to-end:
- Extract the hook's Python into a callable function (or invoke it as subprocess)
- Seed a contradiction in the store, write a conflicting entry, verify quarantine
- If full subprocess test is impractical, at minimum call gate_pipeline with the same args the hook constructs and verify the numeric probe fires

**Verification:** Real baseline numbers recorded (Measured). Hook path verified (Operative or Tested with explanation).

## Phase M1 — First field space: observations vs reasoning (GATED)

### M1.1 Add field spaces to registry
- `observations` space: input = observation text only
- `reasoning` space: input = reasoning text only
- Keep `default` blend as co-equal space
- Each gets separate embedding + stored vector

### M1.2 Query-conditioned combiner
- Heuristic weighting: factual queries → observations weight, rationale queries → reasoning weight, unclear → even blend
- Unlearned heuristic — treat as unproven until experiment

### M1.3 GATING EXPERIMENT (mandatory)
- Compare retrieval: single blended space vs observation/reasoning split with combiner
- Test cross-space disagreement as signal for contradiction/quality/drift
- **Pre-registered decision rule:** if split does not beat single-space baseline, does not ship to default scoring

**Verification status required:** Measured (experiment ran, numbers recorded, ship/no-ship decision made per pre-registered rule)

## Phase M2 — Summary and prompt spaces (GATED, higher bar)

- Per-space admission: beat baseline AND pass whole-field redundancy test (mask entire field, not one path)
- Only after M1 experiment complete
- Optional BM25 per-field scorer if lexical axis pursued

## Phase M3 — Mutable / drift spaces (DEFERRED)

- Not built in this work order
- Registry schema reserves room
- Event capture (log_force) already exists for when mutable spaces are declared

## Reporting Standard

Every deliverable reported as exactly one of:
- **Tested:** unit test covers logic (reachability NOT established)
- **Operative:** end-to-end run through real path produced expected effect
- **Measured:** experiment compared to baseline, pre-registered decision made

## Verification Criteria

| # | Criterion | Phase | Status type |
|---|-----------|-------|-------------|
| 1 | `memoryschema eval` runs on clean install without ImportError | E1 | Operative |
| 2 | Retrieval eval runs against real store with --store flag | E1 | Operative |
| 3 | Single-space baseline recorded with actual numbers | E1 | Measured |
| 4 | Hook path quarantines seeded numeric contradiction end-to-end | E2 | Operative |
| 5 | Written memory carries non-null generator_id | E2 | Operative |
| 6 | Ingested examples produce provenance="ingested" entries | E2 | Operative |
| 7 | All 6 embedding input sites use one canonical function | M0 | Tested |
| 8 | Registry holds one space, combiner is identity, baseline unchanged | M0 | Operative |
| 9 | Field split experiment ran with recorded numbers | M1 | Measured |
| 10 | Ship/no-ship decision made per pre-registered rule | M1 | Measured |
