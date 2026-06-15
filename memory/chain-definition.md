<memory:entity schema="4" name="chain-definition" type="semantic" importance="9">
  <memory:description>A chain of reasoning is a sequence of memory events with a defined start (trigger) and end (conclusion)</memory:description>
  <memory:observations>
    <memory:observation>Each step in the chain is a memory entity connected to the next in sequence</memory:observation>
    <memory:observation>The framework has entities, relations, prompt (trigger), reasoning (thinking), observations (facts) — all pieces exist</memory:observation>
    <memory:observation>Missing: the chain as a first-class concept — no way to group memories into an ordered sequence with start/end</memory:observation>
    <memory:observation>Three design options: chain entity (meta-memory), new relation type (NEXT_STEP), or chain attribute (shared ID + step number)</memory:observation>
  </memory:observations>
  <memory:prompt>User defined: a chain of reasoning is a sequence of memory events with a start and an end</memory:prompt>
  <memory:reasoning>The current relation types (DEPENDS_ON, INFORMS) connect memories but don't imply sequential ordering. A chain needs ordering — step 1 before step 2 before step 3. The representation must capture both the sequence and the chain boundary (where it starts and ends).</memory:reasoning>
</memory:entity>
