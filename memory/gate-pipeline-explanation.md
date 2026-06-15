<memory:entity schema="4" name="gate-pipeline-explanation" type="knowledge" importance="7">
  <memory:description>Gate pipeline: 6 stages — validation, provenance, guards, consistency, numeric probe, L0 echo</memory:description>
  <memory:observations>
    <memory:observation>Stage 1 Validation: name required (REJECT if missing), description expected (warning)</memory:observation>
    <memory:observation>Stage 2 Provenance: valid provenance value, ingested requires source element (V13) or REJECT</memory:observation>
    <memory:observation>Stage 3 Guards: provenance mismatch on upsert → QUARANTINE (prevents trust escalation/demotion)</memory:observation>
    <memory:observation>Stage 4 Consistency: near-duplicate detection (cosine sim > 0.95, different description) → QUARANTINE</memory:observation>
    <memory:observation>Stage 5 Numeric probe: contradicting numeric claims via extract_claims matching → QUARANTINE or log</memory:observation>
    <memory:observation>Stage 6 L0 echo: restatement with no new material (Jaccard overlap) → QUARANTINE</memory:observation>
    <memory:observation>Stages 4-6 require embedding vector — embed runs BEFORE gate in hook pipeline</memory:observation>
    <memory:observation>Every verdict logged to memory/audit.jsonl with reasons and warnings</memory:observation>
  </memory:observations>
  <memory:prompt>Explain the gate pipeline stages 1-3</memory:prompt>
  <memory:reasoning>The gate pipeline protects the store from invalid, unattributed, and suspicious writes. Stages 1-2 enforce structural requirements (REJECT). Stage 3 catches provenance conflicts (QUARANTINE). Stages 4-6 use the embedding to detect duplicates, contradictions, and restatements. The pipeline never silently drops — every entry gets a logged verdict.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
