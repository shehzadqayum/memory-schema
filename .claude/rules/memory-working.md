# Memory Protocol — Kernel

**The deterministic layer (CLI + hooks + write gate) does the structuring, escaping,
numbering, and indexing. These five habits are the LLM's part.**

## 1. Recall before substantive work
```bash
memoryschema recall "<topic>" --limit 3
```
Real retrieval, not file reads. Skip only for purely mechanical operations.

## 2. One chain always active — record steps in plain text
`memoryschema chain status` at session start; if none: `memoryschema chain start chain-<topic>`.

After each substantive response:
```bash
memoryschema chain step --stdin [--desc "evolving summary"] [--uses <evidence-memory>] <<'EOF'
What happened, decisions, results. Raw < > & are SAFE here — code escapes them.
EOF
```
- Code auto-numbers the step, validates, indexes (Neo4j+JSONL), rebuilds the L0 index.
- Refresh `--desc` when the summary drifts (every few steps is fine).
- Conclude an investigation: `chain step "Conclusion: ..."` → `chain release` → immediately
  `chain start` the successor (the store must never sit without an active chain).

## 3. Durable facts get standalone memories
```bash
memoryschema remember <kebab-name> --desc "<one line, <=120 chars>" \
  --obs "atomic fact" [--obs "..."] [--uses <target>] [--supersedes <outdated>] [--importance N]
```
Use for: structural levels, validated patterns, user corrections, decisions.
`--supersedes` retires the old memory from recall. Vary `--importance` (1-10 salience;
7 is the overused default — the gate will nudge you).

## 4. Hand-editing memory/*.md is the fallback path only
The PostToolUse hook indexes hand edits; corruption safety differs by format — legacy
v4 XML fails LOUD (exit 2), a broken v5 file is skipped silently (check `sync`).
Full v5 schema reference (needed only when hand-authoring):
`.claude/rules-ondemand/memory-schema.md` · corpus ingestion (deploy with `init --scopes corpus`):
`.claude/rules-ondemand/memory-corpus.md`

## 5. Health
`memoryschema preflight` (deps gate) · `sync` (drift, read-only) · `reconcile` (heals all
three layers to the .md set; also re-embeds stale content via the provenance hash).
Run the package's test suite env-free (hermetic fail-closed), from a source checkout:
`python -m pytest tests/`
