<memory:entity schema="3" name="v4-verification-plan" type="semantic" importance="10">
  <memory:description>Plan for schema v4 — verification axis (basis attribute), gate hardening (numeric + echo probes), MITIGATES relation, salience instrumentation</memory:description>
  <memory:observations>
    <memory:observation>Seven motivating defects D1-D7 from documentation-and-history audit</memory:observation>
    <memory:observation>Pre-work P1-P3: schema.md v3 summary rows, overlapping upsert tables, doctor table missing 3 checks</memory:observation>
    <memory:observation>Phase 0: reconnaissance — confirm 6 assumptions before any code change</memory:observation>
    <memory:observation>Phase 1: schema v4 — basis attribute (measured/inferred/reported), verified_at, generator, embed_model, V14</memory:observation>
    <memory:observation>Phase 2: verification-aware scoring (basis factor) and SUPERSEDES verification guard</memory:observation>
    <memory:observation>Phase 3: MITIGATES relation type, criterion capture on SUPERSEDES, closure discipline</memory:observation>
    <memory:observation>Phase 4: gate stages 5-6 — numeric contradiction probe, L0 echo probe</memory:observation>
    <memory:observation>Phase 5: contradiction-aware reflect — skip contradictory clusters</memory:observation>
    <memory:observation>Phase 6: salience instrumentation — decline logging, eval mode</memory:observation>
    <memory:observation>Phase 7: conditional — session report sequencing fix if workflow skills present</memory:observation>
    <memory:observation>Phase 8: documentation synchronization — single commit, all surfaces</memory:observation>
    <memory:observation>12 verification criteria as final gate</memory:observation>
  </memory:observations>
  <memory:prompt>Verification axis, gate hardening, subject instrumentation plan from defect analysis</memory:prompt>
  <memory:reasoning>Defects trace to a single root: the system has no representation of how claims were obtained, so transcribed counts carry the same authority as measured ones. The basis attribute and verification guard address this structurally. Gate probes and MITIGATES address downstream consequences.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-12-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
