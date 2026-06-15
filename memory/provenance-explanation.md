<memory:entity schema="4" name="provenance-explanation" type="knowledge" importance="7">
  <memory:description>Provenance: declared origin of content — controls scoring, L0 access, SUPERSEDES authority, presentation</memory:description>
  <memory:observations>
    <memory:observation>4 values: first-party (LLM, default), user (explicit user input), derived (consolidation), ingested (external)</memory:observation>
    <memory:observation>Not measured — declared at write time. Immutable after creation (prevents trust escalation via re-save)</memory:observation>
    <memory:observation>Trust multipliers: first-party/user 1.0, derived 0.9, ingested 0.7 (30% scoring penalty)</memory:observation>
    <memory:observation>L0 gating: ingested never enters MEMORY.md — closes injection channel for external content</memory:observation>
    <memory:observation>SUPERSEDES authority: ingested (trust 1) cannot supersede first-party (trust 3)</memory:observation>
    <memory:observation>Gate stage 3: provenance mismatch on upsert → QUARANTINE</memory:observation>
    <memory:observation>V13: ingested requires source element or REJECT</memory:observation>
  </memory:observations>
  <memory:prompt>What does provenance tell us, how is it measured?</memory:prompt>
  <memory:reasoning>Provenance is the memory system's trust model. It's not measured or inferred — it's a declared attribute enforced through immutability. The consequences cascade: scoring penalty reduces visibility of untrusted content, L0 gating keeps it out of the prompt, SUPERSEDES guards prevent it from replacing trusted content, and the gate quarantines provenance conflicts. The design assumes the declaration is honest and enforces that it cannot be changed after the fact.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
