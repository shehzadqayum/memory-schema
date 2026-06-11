# Salience Eval Residual

## Context

Deferred residual from v4 Phase 6 (session 15). The decline instrumentation (log_decline, CLI, guideline) is delivered. What remains is the evaluation mode: a fixture set of ~20 session excerpts labelled write/no-write, scored as precision/recall. Follows the existing eval harness pattern (fixtures.py + metrics.py + eval_cmd.py + test_eval.py).

## Prior Residuals (from [S4] 5bd2970)

- Salience eval mode → addressing (this session)

## Phase 1 — Salience eval mode (single commit)

### 1.1 Fixtures (tests/eval/fixtures.py)
Add `build_salience_fixtures() -> list[dict]`:
- ~20 short session excerpts, each a dict with:
  - `excerpt`: 1-3 sentence text simulating a response moment
  - `decision`: "write" or "decline"
  - `reason`: why (for human readability, not scored)
- Cover the selective-write policy categories:
  - WRITE: decisions, corrections, novel facts, session boundaries
  - DECLINE: mechanical output, duplicates, clarification questions, trivial acknowledgements

### 1.2 Metrics (tests/eval/metrics.py)
Add `evaluate_salience(decisions: list[dict], fixtures: list[dict]) -> dict`:
- Input: list of {"excerpt": str, "decision": "write"|"decline"} from the system under test
- Gold: the fixtures' decision labels
- Output: {"precision": float, "recall": float, "f1": float, "total": int, "correct": int}
- Precision = correct writes / predicted writes
- Recall = correct writes / actual writes in gold

### 1.3 CLI (src/memoryschema/cli/eval_cmd.py)
Add `--mode` option: `retrieval` (default, existing) | `salience`
- In salience mode: load fixtures, present each excerpt, compare against gold labels
- Since there's no live agent to test against, salience mode reports the fixture set and a "baseline" score (all-write or all-decline) as a reference point
- Output: fixture count, baseline precision/recall, ready for integration with an actual decision source

### 1.4 Tests (tests/eval/test_eval.py)
- `test_salience_fixtures_exist`: fixture count ≥ 20
- `test_salience_metrics`: precision/recall against a known decision set
- `test_salience_baseline`: baseline scores computable

## Verification

1. `python -m pytest tests/ -v` — all pass
2. `memoryschema eval --mode salience` runs without error
3. Fixture set has ≥ 20 items with balanced write/decline labels
4. Precision/recall metrics compute correctly against known inputs
