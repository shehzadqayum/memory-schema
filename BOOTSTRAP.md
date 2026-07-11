# Bootstrapping memory-schema into a project

How to adopt the memory system in a **new or existing project**. Every step below is the verified path — the
CLI creates what it needs and the artefacts ship inside the package, so a plain `pip install` is enough.

> **The 60-second version**
> ```bash
> pip install memory-schema[all]
> cd your-project
> memoryschema --project your-project init --with-neo4j    # scaffolds files + .claude/ rules + Neo4j
> memoryschema hook install                                # registers the PostToolUse indexer (once, global)
> memoryschema preflight                                   # expect 5/5 green
> memoryschema chain start chain-getting-started           # then `chain step` / `remember` / `recall`
> ```

---

## 0. Prerequisites

- **Python ≥ 3.11** (the code uses `X | None` types + modern dataclasses).
- **Docker Desktop** — only for the Neo4j graph store. Skip it and the system runs on the JSONL store alone
  (recall degrades to keyword/structure, loudly, never silently).
- **A Voyage API key** (optional) — `VOYAGE_API_KEY` enables embeddings. Without it, indexing still works and
  recall degrades to keyword/BM25 + graph structure.
- **Windows only:** always `export PYTHONUTF8=1 PYTHONIOENCODING=utf-8` before any `memoryschema` call — the
  default cp1252 console crashes on Unicode.

## 1. Install — two modes

**(a) Standalone consumer** — you just want the memory system:
```bash
pip install memory-schema[all]      # [all] pulls neo4j + voyageai + numpy; the base install is click-only
```

**(b) Co-development vendor** — you want to evolve the module alongside your project (the pattern this repo
was built with). Vendor it via `git subtree` so your repo stays self-contained:
```bash
git subtree add --prefix packages/memory-schema <memory-schema-repo-url> main --squash
python -m venv .venv && source .venv/Scripts/activate      # (POSIX: .venv/bin/activate)
pip install -e ".\packages\memory-schema[all]"             # editable — your edits are live
```
The vendored copy is then the canonical source for your project (there is no upstream to re-sync from);
pull module updates later with `git subtree pull` (see §8).

## 2. `memoryschema init` — scaffold the project

```bash
memoryschema --project <name> --root . init [--scopes working[,corpus]] [--with-neo4j]
```
Creates (idempotently — re-running is safe; it converges the `.claude/` artefacts and never clobbers your
compose/.env/toml):

| Path | What |
|------|------|
| `memory/` + `memory/MEMORY.md` | the entity dir + the always-in-context L0 index |
| `docker-compose.yml` | Neo4j container — references `${NEO4J_PASSWORD}` (no secret baked in) |
| `.env` | the generated `NEO4J_PASSWORD` (and it's added to `.gitignore`) |
| `memoryschema.toml` | project config (name; optional store/neo4j/voyage/`retrieval` tuning) |
| `.claude/rules/memory-working.md` | the always-loaded ~534-token protocol **kernel** |
| `.claude/rules-ondemand/memory-schema.md` | the v5 authoring reference (on demand) |
| `.claude/skills/dream-pass/SKILL.md` | the consolidation skill |
| `.claude/rules-ondemand/memory-corpus.md` | *only* with `--scopes …,corpus` |

`--with-neo4j` also pulls + starts the container. `--scopes` selects the on-demand rule set (default
`working`).

## 3. `memoryschema hook install` — the auto-indexer

```bash
memoryschema hook install
```
Registers a **PostToolUse** hook (and a **Stop** hook) in `~/.claude/settings.json`, pointed at the current
interpreter. Now every `Write`/`Edit` of a `memory/*.md` file auto-parses, embeds, and indexes it — the safety
net for hand-edited files. One hook serves all projects (it derives the project root from the file path).
`hook status` / `hook check` inspect it; `hook upgrade` only edits `settings.json` (never the script).

## 4. `memoryschema plugin sync` — keep `.claude/` current

`init` already deployed the `.claude/` artefacts. Use `plugin sync` to **re-sync after a package upgrade**, and
`plugin sync --check` as a **drift gate** (CI / session-start): it MD5s each deployed file against the packaged
source of truth and exits non-zero on drift, writing nothing.
```bash
memoryschema plugin sync --check      # verify; exit 1 on drift
memoryschema plugin sync              # reconcile (write only what differs)
```

## 5. Backend up + verify

```bash
memoryschema neo4j up        # start the container (skip if you ran init --with-neo4j)
memoryschema preflight       # the always-on dependency gate
```
`preflight` expects **5/5 green** (Docker engine · Neo4j container · bolt · schema · Voyage). It auto-recovers a
merely-stopped container and reports a loud failure otherwise — never a silent JSONL fallback. Voyage is a soft
dep: without a key it degrades with a warning, still green overall.

## 6. First memory — the kernel habits

```bash
memoryschema chain start chain-getting-started         # one chain is always active
memoryschema chain step --stdin <<'EOF'                # working memory — plain text in, code structures it
Set up the memory system; verified preflight 5/5.
EOF
memoryschema remember api-rate-limit \                 # a durable fact
  --desc "The upstream API caps at 100 req/min per key" \
  --obs "429s above ~100/min; back off 60s" --importance 6
memoryschema recall "rate limiting"                    # semantic search across it all
```
Recall before substantive work; record steps with `chain step`; durable facts via `remember`. The always-loaded
kernel (`.claude/rules/memory-working.md`) states these five habits for the agent.

## 7. Verification checklist

- `memoryschema preflight` → 5/5 (or 4/5 with a Voyage warning if no key).
- `memoryschema sync` → `.md` / JSONL / Neo4j counts match (`in sync`).
- Write a `memory/*.md` file by hand → the hook indexes it (see `memoryschema status` node count rise).
- `memoryschema plugin sync --check` → in-sync (the deployed `.claude/` matches the package).

## 8. Upgrades, drift & troubleshooting

- **Update a vendored module:** `git subtree pull --prefix packages/memory-schema <url> main --squash`, then
  `pip install -e ".\packages\memory-schema[all]"` and `memoryschema plugin sync` to redeploy the artefacts.
- **After bulk `.md` edits:** `memoryschema reconcile` rebuilds JSONL from the `.md` set, pushes Neo4j, prunes,
  and verifies (idempotent; `sync` inspects drift read-only first).
- **Eval your corpus (optional):** drop a `eval-gold.jsonl` (`{query, relevant, kind}` per line) at the project
  root and run `memoryschema eval --mode ablation` / `--mode backends`.

| Problem | Fix |
|---------|-----|
| `memoryschema: command not found` | `pip install memory-schema` (or activate the venv it's installed in) |
| Neo4j connection refused | `memoryschema preflight` (auto-starts the container) or `neo4j up` |
| Recall returns keyword-only | `VOYAGE_API_KEY` not set — embeddings degraded (expected, loud) |
| `.claude/` drifted | `memoryschema plugin sync` |
| Unicode crash on Windows | `export PYTHONUTF8=1 PYTHONIOENCODING=utf-8` |
