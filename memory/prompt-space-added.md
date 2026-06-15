<memory:entity schema="4" name="prompt-space-added" type="semantic" importance="5">
  <memory:description>Added prompt embedding space — 5 spaces now active (5120 max dims per entry)</memory:description>
  <memory:observations>
    <memory:observation>Prompt space isolates the user input that triggered the memory — captures intent separately from response</memory:observation>
    <memory:observation basis="measured">36/58 entries have prompt text (62% coverage), 22 skipped as structural absence</memory:observation>
    <memory:observation>Previously prompt was only in reasoning space (combined with reasoning text) — now also available standalone</memory:observation>
    <memory:observation>5 spaces: default (all fields), observations (facts), reasoning (rationale+prompt), description (summary), prompt (user input)</memory:observation>
  </memory:observations>
  <memory:prompt>User requested adding prompt as a separate embedding space</memory:prompt>
  <memory:reasoning>Earlier evaluation recommended skipping prompt space due to short text (avg 43 chars) and redundancy with reasoning space. User overrode this — having the raw user intent as a separate vector enables intent-based retrieval independent of the system response.</memory:reasoning>
</memory:entity>
