# memory-schema

File-first memory system for LLM agents — schema v5 entities (YAML frontmatter +
markdown body), a deterministic CLI write path, JSONL/Neo4j dual storage, Voyage AI
multi-space embeddings, and Claude Code hook integration.

> **The single source of truth for how this system works is
> [`docs/harness-manual.md`](docs/harness-manual.md).**
> This README is a quickstart; on any divergence, the specification wins.

## Quickstart

> Adopting this in a new or existing project? See **[BOOTSTRAP.md](BOOTSTRAP.md)** for the full
> install → `init` → hook → preflight → first-memory walkthrough (both pip and git-subtree modes).

```bash
pip install memory-schema[all]          # or vendor it (git subtree) into your project
cd ~/Projects/my-project
memoryschema --project my-project init --scopes working --with-neo4j
memoryschema hook install
export VOYAGE_API_KEY=voy-xxxxx        # or put it in .env — auto-loaded by CLI and hook
# entities are authored in v5 by default; set MEMORYSCHEMA_V4=1 (or MEMORYSCHEMA_V5=0) only to author legacy v4
memoryschema preflight && memoryschema status
```

Note `--project` is a **group-level** option — it comes before the subcommand.

## The write path (how memories are created)

Plain text in; code does the structuring, escaping, numbering, and indexing
(spec §4 — hand-authored markup corrupting the store is impossible by construction):

```bash
# working memory: one active chain, steps auto-numbered into the v5 ## Log
memoryschema chain start chain-my-investigation
memoryschema chain step --stdin --desc "evolving summary" <<'EOF'
What happened, decisions, results. Raw < > & are safe here.
EOF
memoryschema chain release

# durable facts
memoryschema remember api-rate-limit \
  --desc "The upstream API caps at 100 req/min per key" \
  --obs "429s observed above ~100/min; back off 60s" \
  --importance 6 --uses chain-my-investigation

# temporal facts: same --key => deterministic supersession + point-in-time recall
memoryschema remember config-timeout-july --desc "..." --obs "..." --key config.timeout
memoryschema recall "request timeout" --as-of 2026-06-15
```

Every write parses → authorizes (active-chain model) → embeds (7 spaces, one batched
call) → gates (reject/quarantine) → **dual-writes Neo4j AND JSONL** → regenerates the
`MEMORY.md` L0 index. Hand-editing `memory/*.md` still works — the PostToolUse hook
indexes it — but is the fallback path, not the primary one.

## Retrieval

```bash
memoryschema recall "query" --limit 5      # semantic cascade + rerank + telemetry
memoryschema search "keyword"              # plain keyword/fulltext
memoryschema get <name>  ·  list  ·  status
```

Scoring blends recency, importance, and variance-weighted multi-space relevance;
results cascade through relations, backlinks, and k-NN associations (spec §6).

## Consolidation & telemetry

```bash
memoryschema dream          # read-only candidate report (distill/merge/stale/promote)
memoryschema attribution    # which recalled memories actually get cited
memoryschema recall-stats   # retrieval telemetry
```

The dream pass: code discovers candidates, an LLM session judges, safe primitives act
(spec §7–8).

## Health

```bash
memoryschema preflight      # dependency gate (auto-starts a stopped Neo4j container)
memoryschema sync           # read-only three-layer drift report
memoryschema reconcile      # heal JSONL + Neo4j + L0 to the memory/*.md set
memoryschema doctor         # full diagnostic suite
```

## Install extras

| extra | provides |
|-------|----------|
| *(none)* | JSONL store, keyword search — stdlib + click only |
| `[neo4j]` | Neo4j graph store (neo4j ≥ 5.0) |
| `[embeddings]` | Voyage AI embeddings (voyageai ≥ 0.3, lazy-imported) |
| `[numpy]` | vectorized scoring + the `.npz` vector sidecar (pure-Python fallback without) |
| `[all]` / `[all,dev]` | everything / + pytest toolchain |

## Degradation model

| dependency down | behavior |
|-----------------|----------|
| Neo4j | reads degrade to JSONL with a **loud stderr banner**; `index`/`write`/`import` hard-fail by default (`MEMORYSCHEMA_REQUIRE_NEO4J=false` to relax); `remember`/`chain step` degrade to the JSONL leg with a warning; heal drift with `reconcile` |
| Voyage | indexed unembedded (warning); recall degrades to keyword/structure |
| Docker engine | as Neo4j; preflight reports "start Docker Desktop" (never auto-started) |
| numpy | vectors inline in store.jsonl; pure-Python scoring |

Nothing degrades silently (spec §9 + per-layer matrices).

## Hooks (Claude Code)

`memoryschema hook install` registers the PostToolUse (Write|Edit matcher, 10 s) and
Stop (5 s) hooks in `~/.claude/settings.json` with the current interpreter path
embedded. `hook status / check / scan / upgrade` manage them. The PostToolUse script (package source)
carries local patches — Windows path normalization, project `.env` autoload, and an allowlisted `.env`
export — that change only if the package files are replaced; no `memoryschema` command regenerates the
script (`hook upgrade` only edits `settings.json`).

Hybrid scope: the hook writes to the project's `memory/` when the written file is under
one, falling back to `~/.claude/memory/` for user-level knowledge.

## Testing

```bash
cd packages/memory-schema && python -m pytest tests/    # env-free, hermetic
```

~870 tests across 56 files; external services mocked; a conftest tripwire guards the
live Neo4j store when real credentials are present. The suite is the
rebuild-verification map (spec §13). `memoryschema doctor` verifies a live deployment.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `memoryschema: command not found` | `pip install memory-schema` (or activate the venv it's installed in) |
| Neo4j connection refused | `memoryschema preflight` (auto-starts the container) or `neo4j up` |
| No semantic search results | set `VOYAGE_API_KEY` (`.env`), then `memoryschema embed --all` |
| Hook not firing | `memoryschema hook status` / `hook check` |
| Unicode crash on Windows console | `export PYTHONUTF8=1 PYTHONIOENCODING=utf-8` |
| Layers disagree / stale entries | `memoryschema sync` then `memoryschema reconcile` |

## Documentation

- [`docs/harness-manual.md`](docs/harness-manual.md) — **the
  single source of truth** (schema, write path, storage, retrieval, telemetry,
  consolidation, ops, config, complete CLI, test map)
- [`docs/hierarchy-and-inheritance.md`](docs/hierarchy-and-inheritance.md) — project
  nesting + config/rules inheritance deep-dive (non-normative)
- [`docs/design/`](docs/design/), [`docs/plans/`](docs/plans/),
  [`docs/reports/`](docs/reports/) — historical design records and session reports
- [`CHANGELOG.md`](CHANGELOG.md) — change history

## License

MIT
