<memory:entity schema="4" name="provenance-ambiguity" type="knowledge" importance="8">
  <memory:description>Provenance introduces trust ambiguity — self-declared labels, effectively binary, basis attribute is the better mechanism</memory:description>
  <memory:observations>
    <memory:observation>Provenance is self-declared — LLM labels its own content as first-party trust 3, no verification</memory:observation>
    <memory:observation>3 of 4 provenance values map to the same trust level (3) — the hierarchy is effectively binary (trusted vs ingested)</memory:observation>
    <memory:observation>Nothing prevents setting provenance="user" on LLM-generated content — the declaration is unverifiable</memory:observation>
    <memory:observation>The basis attribute on observations (measured/inferred/reported) is per-observation and epistemological — better trust mechanism</memory:observation>
    <memory:observation>basis describes HOW a fact was established, provenance describes WHO wrote the entity — basis is more meaningful</memory:observation>
    <memory:observation>Provenance enforcement (L0 gating, SUPERSEDES guards) only matters for ingested content — could be a boolean flag</memory:observation>
  </memory:observations>
  <memory:prompt>Provenance introduces ambiguity — trust levels ambiguity — into the framework</memory:prompt>
  <memory:reasoning>The provenance system creates a false sense of trust granularity. Three values (first-party, user, derived) are treated identically at trust level 3. The only meaningful distinction is ingested (external, untrusted). The basis attribute already provides per-observation trust that is epistemologically grounded (measured vs inferred vs reported). Provenance is a blunt instrument where basis is precise.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
