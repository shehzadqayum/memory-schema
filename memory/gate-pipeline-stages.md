---
schema: 5
importance: 7
status: archived
---

Write gate: 6-stage pipeline producing ACCEPT/REJECT/QUARANTINE verdicts

## Observations

- Stage 1 Validation: name required, description expected
- Stage 2 Provenance: valid provenance class, ingested requires source (V13)
- Stage 3 Guards: provenance mismatch detection on upsert — prevents trust escalation
- Stage 4 Consistency: embedding similarity check against existing entries (strict mode)
- Stage 5 Numeric probe: extract_claims with qualifier-keyed matching detects contradictions
- Stage 6 L0 echo: Jaccard word overlap + measured conjunction detects restatements
- Stages 4-6 require embedding vector — embed must run BEFORE gate

## Reasoning

The gate pipeline ensures every write gets a verdict. REJECT blocks indexing. QUARANTINE saves the entry with quarantined status and strips its embedding. ACCEPT proceeds to upsert. The pipeline never silently drops an entry.

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
