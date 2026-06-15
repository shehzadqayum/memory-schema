<memory:entity schema="4" name="chain-live-accumulation-design" type="semantic" importance="9">
  <memory:description>Live chain entity: created if absent, updated every response, released at end of cycle</memory:description>
  <memory:observations>
    <memory:observation>Live chains grow through upsert append semantics — each response adds a step observation</memory:observation>
    <memory:observation>Upsert supports this: observations appended, description/reasoning replaced, relations merged</memory:observation>
    <memory:observation>Embedding re-computed on every update (hook fires on write) — chain embedding evolves as it grows</memory:observation>
    <memory:observation>Release at cycle end: finalize description/reasoning, add conclusion observation</memory:observation>
    <memory:observation>Changes mandatory write rule from "new entity per response" to "update active chain per response"</memory:observation>
  </memory:observations>
  <memory:prompt>User proposed: chain created if absent, updated every memory event, released at end of cycle</memory:prompt>
  <memory:reasoning>This shifts chains from retrospective summaries to live accumulating records. The chain entity becomes a running log that grows with the session. Each upsert appends observations (the steps) while replacing the description (evolving summary) and reasoning (evolving narrative). The hook re-embeds on every write, so the chain's vector representation stays current. At release, the chain is a complete record of the reasoning sequence.</memory:reasoning>
  <memory:relations>
    <memory:relation target="chain-entity-design" type="MODIFIES"/>
    <memory:relation target="chain-pattern-formalized" type="MODIFIES"/>
  </memory:relations>
</memory:entity>
