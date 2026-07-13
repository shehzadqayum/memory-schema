---
schema: 5
importance: 6
status: archived
---

Complete listing of all memory entity fields: 3 required, 12 LLM-authored optional, 9 system-managed

## Observations

- Required: schema (attribute), name (attribute), description (child element)
- LLM-authored with embedding spaces: description, observations, prompt, reasoning, chain, name — 6 fields map 1:1 to spaces
- LLM-authored without spaces: type, importance, relations, source, project, provenance, body
- System-managed: embedding, embeddings, divergence_profile, created_at, last_accessed, access_count, verified_at, backlinks, associations
- Upsert behaviors: immutable (name, schema, provenance, project), replaced (description, reasoning, prompt, chain, type, importance), appended (observations), merged (relations)

## Reasoning

The field listing shows the complete data model: what the LLM controls, what the system manages, which fields have embedding spaces, and how each behaves on upsert. The 7 embedding spaces (default + 6 field-specific) cover all text content authored by the LLM.

## Prompt

List all the memory fields

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
