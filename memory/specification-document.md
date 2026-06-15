<memory:entity schema="4" name="specification-document" type="knowledge" importance="8" confidence="9">
  <memory:description>Full memory system specification document generated at docs/memory-system-specification.md — 14 sections</memory:description>
  <memory:observations>
    <memory:observation>14 sections: overview, entity schema, write pipeline, retrieval, spaces, relations, chains, auth, storage, validation, recall, audit, CLI, principles</memory:observation>
    <memory:observation>Covers all 22 fields (13 LLM + 9 system), 7 spaces, 4-stage gate, variance-weighted combiner, chain lifecycle</memory:observation>
    <memory:observation>Includes the 7 design principles: content-agnostic, 1:1 mapping, variance-weighted, immutable default, graceful degradation, confidence for calibration, recall before respond</memory:observation>
    <memory:observation>Based on recalled memories: complete-schematic (0.732), architecture-schematic (0.729)</memory:observation>
  </memory:observations>
  <memory:prompt>Generate a full memory specification description document</memory:prompt>
  <memory:reasoning>The specification consolidates all architectural decisions, pipeline details, and design principles into a single reference document. It was generated after recalling the schematic and architecture memories, ensuring consistency with the established system description.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
