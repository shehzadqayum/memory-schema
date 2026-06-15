<memory:entity schema="4" name="chain-type-attribute-status" type="semantic" importance="6">
  <memory:description>Type attribute and fields partially resolved — chain pattern formalized but type guidance not updated for chain model</memory:description>
  <memory:observations>
    <memory:observation>5 embedding spaces now map 1:1 to entity fields: default, observations, reasoning, description, prompt</memory:observation>
    <memory:observation>Chain entities are always semantic (recency floor 0.6, persists as knowledge distillation)</memory:observation>
    <memory:observation>Standalone memory type guidance still uses old generic descriptions from pre-chain era</memory:observation>
    <memory:observation>Missing: when to use semantic vs episodic vs procedural for standalone memories alongside active chains</memory:observation>
  </memory:observations>
  <memory:prompt>User asked if type attribute and fields have been resolved</memory:prompt>
  <memory:reasoning>The chain model changes the relationship between type and purpose. Before chains, every response produced a standalone memory that needed its own type. Now the chain is the primary accumulator (always semantic) and standalone memories are supplementary — their type guidance should reflect this new role.</memory:reasoning>
</memory:entity>
