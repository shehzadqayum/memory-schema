<memory:entity schema="3" name="docs-alignment-plan" type="semantic" importance="9">
  <memory:description>Plan for full documentation alignment — 6 implementation fixes, audit, then 24 doc fixes across 18 files</memory:description>
  <memory:observations>
    <memory:observation>Neo4j hub bonus uses min(backlinks, 5) but store.py uses math.log(1 + backlinks) — scoring parity bug</memory:observation>
    <memory:observation>docker-compose.yml has hardcoded changeme password — security issue</memory:observation>
    <memory:observation>Example scripts and README use schema="2" — stale</memory:observation>
    <memory:observation>validator.py R6 has dead code: level = 'R6' if strict else 'R6'</memory:observation>
    <memory:observation>24 documentation fixes: doctor count (20→21), validation rules (V1-V10→V1-V13), hub bonus formula, type factor, upsert immutability, 6 missing CLI commands, schema version, module docstrings, config table completeness</memory:observation>
    <memory:observation>Three-pass audit covered every source file, template, hook, example, config, and doc</memory:observation>
  </memory:observations>
  <memory:prompt>Full documentation alignment after v3 semantics implementation</memory:prompt>
  <memory:reasoning>Implementation outpaced documentation across 10 sessions. Three exhaustive audits revealed scoring divergence between backends, stale examples, security issue, and 24 documentation gaps. Plan restructured: fix code first, audit, then align all docs.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-10-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
