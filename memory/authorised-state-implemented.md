<memory:entity schema="4" name="authorised-state-implemented" type="knowledge" importance="9">
  <memory:description>Implemented authorised/unauthorised memory states — only active chain is writable</memory:description>
  <memory:observations>
    <memory:observation>chain_state.py: get/set/release active chain via memory/.active_chain file</memory:observation>
    <memory:observation>Hook blocks upsert to existing memories unless name matches active chain</memory:observation>
    <memory:observation>CLI: memoryschema chain status/start/release</memory:observation>
    <memory:observation>New memories always allowed. Only upserts to existing names are gated.</memory:observation>
    <memory:observation>At most ONE authorised entity at any time. Release makes it read-only permanently.</memory:observation>
    <memory:observation>681 tests passing, 11 new chain state tests</memory:observation>
  </memory:observations>
  <memory:prompt>Implement authorised/unauthorised memory states</memory:prompt>
  <memory:reasoning>The implementation uses a file-based singleton (memory/.active_chain) rather than a field on the entity because authorisation is a system-level state, not an entity property. The hook checks this file before allowing upserts. New writes are always allowed — only mutations to existing entities are gated.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
