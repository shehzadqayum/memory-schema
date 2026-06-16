<memory:entity schema="4" name="retrieval-mechanism-explained" type="knowledge" importance="7" confidence="9">
  <memory:description>Retrieval is explicit CLI call (memoryschema recall via Bash) — not neural, not implicit, auditable</memory:description>
  <memory:observations>
    <memory:observation>Layer 1: LLM runs memoryschema recall via Bash tool before every response (rule-mandated)</memory:observation>
    <memory:observation>Layer 2: inside the call — embed query, score entries (recency+importance+relevance), variance-weighted combiner, cascade through relations/backlinks/k-NN</memory:observation>
    <memory:observation>Layer 3: LLM has no neural access to memories — they're not in weights or context window (except MEMORY.md index)</memory:observation>
    <memory:observation>Mechanism is retrieval-augmented: external store queried at response time, results injected into context</memory:observation>
    <memory:observation>If the LLM forgets to call recall, it doesn't have the memories — the rule is behavioral, not enforced by code</memory:observation>
  </memory:observations>
  <memory:prompt>What is your memory retrieval mechanism?</memory:prompt>
  <memory:reasoning>The honest answer: it's a CLI call, not magic. The LLM runs a bash command, reads the output, and uses it. The sophistication is in what happens inside that command (7-space variance-weighted scoring, cascade), but the interface is a simple tool call. The memories are external, explicit, and auditable — not learned or implicit.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
