<memory:entity schema="3" name="v3-semantics-plan" type="semantic" importance="10">
  <memory:description>Plan for v3 field semantics, precedence fix, and documentation reconciliation — 8 phases</memory:description>
  <memory:observations>
    <memory:observation>Config precedence code correct (CLI last = highest) but docs contradict across 4 files</memory:observation>
    <memory:observation>status/provenance validated (V11/V12) but zero retrieval semantics — no filtering, no trust multiplier</memory:observation>
    <memory:observation>SUPERSEDES propagation undocumented and unguarded (no trust/authority checks)</memory:observation>
    <memory:observation>Write gate has reject but no quarantine operational spec</memory:observation>
    <memory:observation>Type factor (semantic/episodic/procedural) still has no recency modifier</memory:observation>
    <memory:observation>Documentation drift recurred: counts, formulas, schema versions forked again</memory:observation>
    <memory:observation>New issues: backend-divergent max_depth, secrets in TOML, $project_prefix undefined</memory:observation>
  </memory:observations>
  <memory:prompt>v3 semantics specification from re-audit</memory:prompt>
  <memory:reasoning>v3 structural work (fields, validation) complete but semantic half missing — status/provenance are validated metadata that nothing consumes at retrieval time. This plan converts annotation into defense.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-9-close" type="DEPENDS_ON"/>
    <memory:relation target="v3-remediation-plan" type="MODIFIES"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
