<memory:entity schema="4" name="gate-pipeline-stages" type="semantic" importance="7">
  <memory:description>Write gate: 6-stage pipeline producing ACCEPT/REJECT/QUARANTINE verdicts</memory:description>
  <memory:observations>
    <memory:observation>Stage 1 Validation: name required, description expected</memory:observation>
    <memory:observation>Stage 2 Provenance: valid provenance class, ingested requires source (V13)</memory:observation>
    <memory:observation>Stage 3 Guards: provenance mismatch detection on upsert — prevents trust escalation</memory:observation>
    <memory:observation>Stage 4 Consistency: embedding similarity check against existing entries (strict mode)</memory:observation>
    <memory:observation>Stage 5 Numeric probe: extract_claims with qualifier-keyed matching detects contradictions</memory:observation>
    <memory:observation>Stage 6 L0 echo: Jaccard word overlap + measured conjunction detects restatements</memory:observation>
    <memory:observation>Stages 4-6 require embedding vector — embed must run BEFORE gate</memory:observation>
  </memory:observations>
  <memory:reasoning>The gate pipeline ensures every write gets a verdict. REJECT blocks indexing. QUARANTINE saves the entry with quarantined status and strips its embedding. ACCEPT proceeds to upsert. The pipeline never silently drops an entry.</memory:reasoning>
</memory:entity>
