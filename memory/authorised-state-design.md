<memory:entity schema="4" name="authorised-state-design" type="knowledge" importance="9">
  <memory:description>Two memory states: unauthorised (read-only, default) and authorised (read-write, one active chain only)</memory:description>
  <memory:observations>
    <memory:observation>Every memory enters unauthorised (read-only) state after write — permanent, cannot be modified</memory:observation>
    <memory:observation>Only ONE memory can be authorised at a time: the active chain entity</memory:observation>
    <memory:observation>Authorised allows upsert (append observations, replace description/reasoning) — the chain accumulation pattern</memory:observation>
    <memory:observation>Release transitions authorised → unauthorised permanently. New chain creates a new authorised entity.</memory:observation>
    <memory:observation>Hook enforces: reject upserts to unauthorised, allow only to the single authorised chain</memory:observation>
    <memory:observation>SUPERSEDES handles evolution for read-only memories — new entity replaces old, no mutation needed</memory:observation>
  </memory:observations>
  <memory:prompt>We can have two states: unauthorised (read-only, default) and authorised (read-write) — active only for current chain</memory:prompt>
  <memory:reasoning>This solves the unbounded accumulation problem while preserving the live chain pattern. Only one entity is mutable at a time (the active chain). Everything else is a frozen snapshot. The singleton constraint (one authorised entity) prevents the mistake of editing old memories. When the chain releases, the system returns to fully immutable until a new chain is created.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
