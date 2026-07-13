---
schema: 5
importance: 7
relations:
  - USES memoryschema-preextraction-audit
---

PLAN (2026-07-11): split memory-schema into a single schema authority (schema_def+prose+conformance test) vs harness manual

## Observations

- PLAN FILE: C:/Users/Caldera/.claude/plans/proceed-to-develop-a-steady-horizon.md (full detail there). Developed 2026-07-11, plan mode, NOT executed. DECISIONS taken: (1) schema authority form = machine-readable single source + prose + conformance test (not prose-only); (2) execution scope = authority+split FIRST, code/security fixes tracked as separately-approved follow-ups. Root problem it fixes: the 61KB memory-system-specification.md conflates the SCHEMA (entity-model authority) with the HARNESS manual (mechanics), and the schema is defined in 3 disagreeing places (prose spec, config.py:13-24 constants, and two mismatched regexes validator.KEBAB_CASE vs format_v5._REL_RE); SCHEMA_VERSION in code is still 4 while files carry schema:5. Follows the harness-conforms-to-schema doctrine from [[memoryschema-preextraction-audit]] step 78.
- PART A - EXECUTE NOW: (A1) new src/memoryschema/schema_def.py = the ONE authority (fields, enums+per-relation semantics, ONE kebab name/target grammar [corpus is 100% kebab -> zero-rename], separate fact-key grammar <kebab>(.<kebab>)+, V/R/Q invariants as predicates, temporal+supersession model, SCHEMA_VERSION=5); config.py/validator.py/format_v5.py re-export from it (non-behavioral). (A2) docs/schema-specification.md NORMATIVE = spec sec3 + semantic halves of 3.3/4.5/4.6 + sec14 invariants. (A3) rename remainder -> docs/harness-manual.md; repoint .claude-plugin/rules-ondemand/memory-schema.md:7, README, CLAUDE.md, index.md:101. (A4) tests/test_schema_conformance.py asserts config/validator/format_v5/doc == schema_def; the Part-B gaps are xfail(tracked) so failing assertions ARE the follow-up worklist.
- PART B (tracked follow-up = harness adapts UP to schema, each gated by an A4 xfail): B1 v5 entities bypass all V/R/Q validation (validator v4-only, validator.py:76-79) -> dispatch validate() on format; B2 create_entity_file defaults to v4 XML unless MEMORYSCHEMA_V5=1 (write_index.py:406-418) -> flip default to v5; B3 malformed v5 file silently PRUNED (reconcile guard keys on <memory:entity, reconcile.py:89-95) = data loss -> extend guard+test; B4 SCHEMA_VERSION=4 stale (config.py:24) -> bump 5; B5 optional policy desc<=120 warn-only. PART C (re-classified audit issues): security HIGH-1 preflight docker-compose-up untrusted CWD + HIGH-2 hook exports all .env keys = HARNESS/ops fixes, separate gating workstream; cross-project-injection MED -> schema provenance/trust field; multi-space-live + relations-collapse-abandoned + LLM-importance = decisions recorded in the schema authority. EXTRACTION GATE: all conformance xfails resolved + both HIGHs fixed + compose template parameterized + manual true to code.

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
