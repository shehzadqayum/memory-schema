<memory:entity schema="4" name="provenance-removed" type="knowledge" importance="9">
  <memory:description>Provenance removed from entire framework — code, tests, and documentation synchronized</memory:description>
  <memory:observations>
    <memory:observation>Removed from config.py: VALID_PROVENANCES, TRUST_LEVELS constants</memory:observation>
    <memory:observation>Removed from tags.py: provenance attribute parsing</memory:observation>
    <memory:observation>Removed from validator.py: V12 (provenance validation), V13 (ingested requires source)</memory:observation>
    <memory:observation>Removed from write_gate.py: stage 2 (provenance admission), stage 3 (provenance mismatch guards) — gate is now 4 stages</memory:observation>
    <memory:observation>Removed from store.py: trust multiplier in scoring, trust guard in SUPERSEDES. Verification guard (basis-based) retained.</memory:observation>
    <memory:observation>Removed from neo4j_store.py: trust guard, trust multiplier, provenance in upsert</memory:observation>
    <memory:observation>Removed from hook: L0 provenance gating (all memories now enter MEMORY.md)</memory:observation>
    <memory:observation>Removed from docs/schema.md: provenance semantics section, trust hierarchy, L0 gating, V12/V13 rules</memory:observation>
    <memory:observation>Removed from .claude/rules/: provenance field, trust references, gate stage count updated</memory:observation>
    <memory:observation>8 test methods removed, 669 tests passing</memory:observation>
    <memory:observation>Trust is now handled by basis attribute (per-observation, epistemological) not provenance (per-entity, categorical)</memory:observation>
  </memory:observations>
  <memory:prompt>Remove provenance from the entire framework</memory:prompt>
  <memory:reasoning>Provenance introduced false trust granularity — 4 values mapped to effectively 2 trust levels (trusted=3 vs ingested=1). The basis attribute on observations provides better per-observation trust grounding (measured/inferred/reported). Removing provenance simplifies the framework: fewer gate stages, no trust multiplier, no L0 gating by content origin. The verification guard (basis-based SUPERSEDES check) is retained as the correct trust mechanism.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
