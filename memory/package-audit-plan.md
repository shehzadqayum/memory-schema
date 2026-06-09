<memory:entity schema="2" name="package-audit-plan" type="semantic" importance="9">
  <memory:description>Full package audit plan — 13 findings across CRITICAL/HIGH/MEDIUM/LOW</memory:description>
  <memory:observations>
    <memory:observation>CRITICAL: Cypher injection via f-string in neo4j_store.py:109-113 — rel_type interpolated into query, allowlist is only guard</memory:observation>
    <memory:observation>HIGH: Neo4j project scoping missing OR m.project IS NULL for unscoped entities — diverges from JSONL store behavior</memory:observation>
    <memory:observation>HIGH: Relation type constants duplicated in 4 files (config, validator, neo4j_store, migration)</memory:observation>
    <memory:observation>HIGH: tags.py defaults type to empty string instead of semantic (line 75)</memory:observation>
    <memory:observation>HIGH: Hook script silent failure when both Neo4j and JSONL fail — 2&gt;/dev/null suppresses stderr</memory:observation>
    <memory:observation>HIGH: tomllib import without Python 3.10 fallback (requires-python says &gt;=3.10)</memory:observation>
    <memory:observation>MEDIUM: Duplicated scoring logic between _score_entry and _score_all_entries numpy path</memory:observation>
    <memory:observation>MEDIUM: Upsert merges filepath and schema — unclear mutability semantics</memory:observation>
    <memory:observation>MEDIUM: _derive_project can produce invalid project names from malformed paths</memory:observation>
    <memory:observation>LOW: Dead imports in tags.py (os, discover_memory_files)</memory:observation>
  </memory:observations>
  <memory:reasoning>Three parallel audit agents covered core data path, integration modules, and CLI/tests/package. All agent findings verified against current code — 4 claims disproven. 390 tests passing, package fundamentally sound but needs defense-in-depth improvements.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-4-close" type="DEPENDS_ON"/>
    <memory:relation target="inheritance-review-fixes" type="MODIFIES"/>
  </memory:relations>
  <memory:source>session-5-plan</memory:source>
  <memory:project>memory-schema</memory:project>
</memory:entity>

Plan location: `.claude/plans/polymorphic-rolling-mccarthy.md`
Prior residuals: None (from [S4] b3226f3).
