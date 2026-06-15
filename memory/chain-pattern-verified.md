<memory:entity schema="4" name="chain-pattern-verified" type="procedural" importance="8">
  <memory:description>Chain entity pattern verified: chains surface as top result, cascade follows USES to evidence</memory:description>
  <memory:observations>
    <memory:observation basis="measured">Chain entities score 0.72-0.78 for their trigger questions — highest among all results</memory:observation>
    <memory:observation basis="measured">USES relations pull evidence memories into recall results via cascade (depth 1-2)</memory:observation>
    <memory:observation basis="measured">Three chains created and tested: equal-weight-fails, hook-investigation, memory-quality-evolution</memory:observation>
    <memory:observation>Chain observations provide the ordered summary; cascade provides the detailed evidence</memory:observation>
    <memory:observation>Pattern requires zero schema changes — uses existing entity structure, observations for steps, USES for evidence</memory:observation>
  </memory:observations>
  <memory:prompt>Do chain entities work with recall cascade?</memory:prompt>
  <memory:reasoning>The chain entity is a semantic memory (recency floor 0.6, persists) that embeds the full reasoning sequence in its observations and links to evidence via USES. When recalled, it surfaces as the top result and the cascade pulls in supporting memories. This creates a knowledge distillation pattern: individual episodic steps may decay, but the chain persists as a semantic summary with links back to evidence.</memory:reasoning>
</memory:entity>
