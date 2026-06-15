<memory:entity schema="4" name="chain-implementing-live-chains" type="semantic" importance="8">
  <memory:description>Chain: implementing live accumulating chain entities — formalizing the pattern in schema and rules</memory:description>
  <memory:observations>
    <memory:observation>Step 1: User defined chain as sequence of memory events with start and end</memory:observation>
    <memory:observation>Step 2: Chose chain entity approach — meta-memory with ordered step observations and USES relations</memory:observation>
    <memory:observation>Step 3: Created 3 retrospective chains (equal-weight-fails, hook-investigation, memory-quality) — verified recall works</memory:observation>
    <memory:observation>Step 4: Formalized pattern in docs/schema.md, .claude/rules/memory-schema.md (Rule 9), .claude/rules/memory-working.md</memory:observation>
    <memory:observation>Step 5: User proposed live accumulation — create if absent, update every response, release at cycle end</memory:observation>
    <memory:observation>Step 6: Updated all 3 docs to reflect live chain model — upsert append semantics, evolving description/reasoning, re-embedding on every update</memory:observation>
    <memory:observation>Step 7: Changed working memory enforcement from "new entity per response" to "maintain active chain + standalone memories for durable facts"</memory:observation>
  </memory:observations>
  <memory:prompt>How should reasoning chains be captured in the memory system?</memory:prompt>
  <memory:reasoning>The chain evolved from retrospective summary (created after the fact) to live accumulator (growing with each response). The upsert semantics already support this: observations append, description/reasoning replace, relations merge. The hook re-embeds on every write. This is the first live chain — it will be released when the implementation is complete.</memory:reasoning>
  <memory:relations>
    <memory:relation target="chain-entity-design" type="USES"/>
    <memory:relation target="chain-pattern-formalized" type="USES"/>
    <memory:relation target="chain-live-accumulation-design" type="USES"/>
  </memory:relations>
</memory:entity>
