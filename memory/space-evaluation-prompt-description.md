<memory:entity schema="4" name="space-evaluation-prompt-description" type="semantic" importance="7">
  <memory:description>Evaluation: description space worth adding (high discriminative power), prompt space not (redundant with reasoning)</memory:description>
  <memory:observations>
    <memory:observation basis="measured">Prompt field: 60% coverage, avg 43 chars, already in reasoning space — low value as separate space</memory:observation>
    <memory:observation basis="measured">Description field: 100% coverage, avg 82 chars, only in default blend — not in any field-specific space</memory:observation>
    <memory:observation basis="measured">Description diverges from default by 0.35-0.47 gap on pairs with high default similarity (0.70-0.83)</memory:observation>
    <memory:observation basis="measured">Example: type-system-explanation ↔ memory-quality-lesson — default sim 0.788 but description sim 0.322</memory:observation>
    <memory:observation basis="inferred">Description captures compressed topic identity distinct from observation facts and reasoning rationale</memory:observation>
  </memory:observations>
  <memory:prompt>User asked to evaluate adding prompt and description embedding spaces</memory:prompt>
  <memory:reasoning>Ran empirical analysis on 43 active entries. Prompt space adds little: short text, low coverage, already in reasoning space. Description space shows genuine discriminative power — entries that blend together in the default space have very different descriptions, suggesting the one-line summary is a strong semantic anchor worth isolating.</memory:reasoning>
</memory:entity>
