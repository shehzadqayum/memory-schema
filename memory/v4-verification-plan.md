---
schema: 5
importance: 10
status: archived
---

Plan for schema v4 — verification axis (basis attribute), gate hardening (numeric + echo probes), MITIGATES relation, salience instrumentation

## Observations

- Seven motivating defects D1-D7 from documentation-and-history audit
- Pre-work P1-P3: schema.md v3 summary rows, overlapping upsert tables, doctor table missing 3 checks
- Phase 0: reconnaissance — confirm 6 assumptions before any code change
- Phase 1: schema v4 — basis attribute (measured/inferred/reported), verified_at, generator, embed_model, V14
- Phase 2: verification-aware scoring (basis factor) and SUPERSEDES verification guard
- Phase 3: MITIGATES relation type, criterion capture on SUPERSEDES, closure discipline
- Phase 4: gate stages 5-6 — numeric contradiction probe, L0 echo probe
- Phase 5: contradiction-aware reflect — skip contradictory clusters
- Phase 6: salience instrumentation — decline logging, eval mode
- Phase 7: conditional — session report sequencing fix if workflow skills present
- Phase 8: documentation synchronization — single commit, all surfaces
- 12 verification criteria as final gate

## Reasoning

Defects trace to a single root: the system has no representation of how claims were obtained, so transcribed counts carry the same authority as measured ones. The basis attribute and verification guard address this structurally. Gate probes and MITIGATES address downstream consequences.

## Prompt

Verification axis, gate hardening, subject instrumentation plan from defect analysis

## Notes

Migrated from genesis 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: DEPENDS_ON session-12-close.
