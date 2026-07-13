---
schema: 5
importance: 9
status: archived
---

The LLM never recalled memories during this conversation — the system is write-only in practice

## Observations

- Not once did the LLM call memoryschema recall or store.recall() to inform a response
- Every response used file I/O (Read tool), code execution, or conversation context — not semantic retrieval
- MEMORY.md is loaded via rules but that's a static index, not ranked retrieval
- The recall pipeline works (demonstrated multiple times) but is not wired into response generation
- For recall to inform responses: needs PreToolUse hook, rules instruction to recall before answering, or MCP server

## Reasoning

This is the most important finding of the session. We built a complete write pipeline (parse, embed, gate, store, index) and a complete retrieval system (scoring, variance combiner, cascade) but never connected retrieval to response generation. The system captures knowledge but doesn't use it. The next step is closing the loop: automatic recall before responses.

## Prompt

Has the LLM been recalling any memories?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
