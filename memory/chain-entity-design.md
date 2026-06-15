<memory:entity schema="4" name="chain-entity-design" type="semantic" importance="9">
  <memory:description>Chain entity design: a meta-memory listing ordered steps as observations with USES relations to evidence</memory:description>
  <memory:observations>
    <memory:observation>A chain entity is a regular memory entity — no schema changes needed</memory:observation>
    <memory:observation>Steps are listed as ordered observations: "Step 1: ...", "Step 2: ...", "Conclusion: ..."</memory:observation>
    <memory:observation>USES relations link the chain to the individual evidence memories</memory:observation>
    <memory:observation>The chain has its own prompt (trigger question), reasoning (why the chain matters), description (summary/conclusion)</memory:observation>
    <memory:observation>Chain entities are embeddable in all 5 spaces — findable by the trigger question, the conclusion, or any step</memory:observation>
    <memory:observation>Recall cascade follows USES relations to surface the full evidence set from the chain</memory:observation>
  </memory:observations>
  <memory:prompt>User chose chain entity approach for representing reasoning chains</memory:prompt>
  <memory:reasoning>The chain entity pattern requires zero schema changes — it uses existing entity structure, observations for ordered steps, and USES relations for evidence linking. The chain itself becomes a semantic summary that persists (recency floor 0.6) while the individual evidence steps may be episodic and decay. This creates a natural knowledge distillation pattern.</memory:reasoning>
</memory:entity>
