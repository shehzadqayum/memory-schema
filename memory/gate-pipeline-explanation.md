---
schema: 5
importance: 7
status: archived
---

Gate pipeline: 6 stages — validation, provenance, guards, consistency, numeric probe, L0 echo

## Observations

- Stage 1 Validation: name required (REJECT if missing), description expected (warning)
- Stage 2 Provenance: valid provenance value, ingested requires source element (V13) or REJECT
- Stage 3 Guards: provenance mismatch on upsert → QUARANTINE (prevents trust escalation/demotion)
- Stage 4 Consistency: near-duplicate detection (cosine sim > 0.95, different description) → QUARANTINE
- Stage 5 Numeric probe: contradicting numeric claims via extract_claims matching → QUARANTINE or log
- Stage 6 L0 echo: restatement with no new material (Jaccard overlap) → QUARANTINE
- Stages 4-6 require embedding vector — embed runs BEFORE gate in hook pipeline
- Every verdict logged to memory/audit.jsonl with reasons and warnings

## Reasoning

The gate pipeline protects the store from invalid, unattributed, and suspicious writes. Stages 1-2 enforce structural requirements (REJECT). Stage 3 catches provenance conflicts (QUARANTINE). Stages 4-6 use the embedding to detect duplicates, contradictions, and restatements. The pipeline never silently drops — every entry gets a logged verdict.

## Prompt

Explain the gate pipeline stages 1-3

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
