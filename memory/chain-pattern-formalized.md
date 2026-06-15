<memory:entity schema="4" name="chain-pattern-formalized" type="semantic" importance="8">
  <memory:description>Chain entity pattern formalized in schema spec, rules, and working guidelines</memory:description>
  <memory:observations>
    <memory:observation>Added to docs/schema.md: full spec with structure, XML example, retrieval behavior, when-to-create guidance</memory:observation>
    <memory:observation>Added to .claude/rules/memory-schema.md: Rule 9 — concise chain pattern definition (loaded into every conversation)</memory:observation>
    <memory:observation>Added to .claude/rules/memory-working.md: chain creation guidance — prefer one chain over multiple disconnected episodics</memory:observation>
    <memory:observation>Pattern: chain- prefix, semantic type, ordered step observations, USES relations to evidence, trigger as prompt</memory:observation>
  </memory:observations>
  <memory:prompt>User asked to formalize the chain entity pattern in documentation</memory:prompt>
  <memory:reasoning>The chain pattern was working empirically but undocumented. Formalizing in the schema spec (source of truth), rules file (loaded every conversation), and working guidelines (behavioral instruction) ensures future sessions know the pattern exists and how to apply it. The rules file is the critical one — it's in every conversation's system prompt.</memory:reasoning>
  <memory:relations>
    <memory:relation target="chain-entity-design" type="SUPERSEDES"/>
    <memory:relation target="chain-not-formalized" type="SUPERSEDES"/>
  </memory:relations>
</memory:entity>
