# memory-schema documentation map

| document | role |
|----------|------|
| [`harness-manual.md`](harness-manual.md) | **THE SINGLE SOURCE OF TRUTH** — the complete, normative, rebuildable-from-scratch specification (schema, write path, storage, retrieval, telemetry, consolidation, ops, config, CLI, test map). Every other document defers to it. |
| [`hierarchy-and-inheritance.md`](hierarchy-and-inheritance.md) | Feature deep-dive: project nesting, config/rules inheritance (non-normative satellite of spec §10.4) |
| [`design/`](design/) | Historical design documents (bannered; includes proposals that were never implemented) |
| [`plans/`](plans/) | Historical implementation plans (bannered) |
| [`reports/`](reports/) | Historical session reports — a development audit trail, not living documentation |
| [`eval/`](eval/), [`logs/`](logs/) | Evaluation artifacts and skill-execution logs |

Deleted 2026-07-05 (superseded by the specification; recover via git history):
`schema.md`, `technical-reference.md`, `implementation-guide.md`, `system-overview.md`.

LLM-facing derived references (deployed to a project's `.claude/`): the always-loaded kernel
`.claude/rules/memory-working.md` and the on-demand `.claude/rules-ondemand/memory-schema.md`.
