# Memory System Setup & Issues Report — Trading-Journal Deployment (2026-06-21)

**Context:** First real-world deployment of `memory-schema` as the backend for an Obsidian trading
journal on **Windows**. This report documents the full setup and — per the brief — **every issue
encountered and its fix**, written for *memory development* (i.e. upstream feedback to this package).
Many issues are Windows-specific and the package had clearly not been exercised on Windows before.

**Companion document:** the wiki/Obsidian front-end is documented separately at
`MQL4/Files/Analysis/docs/wiki-setup-report.md`.

**Updated 2026-06-22:** §10 adds two **continued-use findings** surfaced while building the journal's
periodic performance reports — **M14** (an unescaped `<` in observation text silently truncates the store
through strict XML parsing) and **M15** (the append-only chain accumulates stale observation variants with
no non-destructive resync). Both are read/observability-layer integrity issues; see §10 and the new §6
recommendations 9–10.

---

## 1. Environment

| Component | Value |
|-----------|-------|
| OS | Windows 10 Pro 19045 |
| Shell | Git Bash (`/usr/bin/bash`) invoked from Claude Code |
| Python | 3.13.3 (`C:\Python\Python313`); note: `python3` alias absent, only `python` |
| pip | 25.0.1 |
| Docker | 28.1.1, Compose v2.35.1 (daemon running) |
| Package | `memory-schema` 0.1.0 (editable install from `packages/memory-schema`) |
| Neo4j | `neo4j:5.26-community` (container `trading-journal-neo4j`) |
| Voyage | `voyage-4-lite`, 1024-dim; key sourced from `VoyageAIKey.txt` at terminal root |
| Memory project root | `R:\…\MQL4\Files\Analysis` (project name `trading-journal`) |

## 2. Setup sequence (chronological, as executed)

1. `python -m pip install -e "packages/memory-schema[all]"` — installs CLI + neo4j + voyageai + numpy.
2. `memoryschema --project trading-journal init --scopes working,corpus` — created `memory/MEMORY.md`,
   `docker-compose.yml`, `.env.example`, `.claude/rules/memory-{schema,working,corpus}.md`,
   `memoryschema.toml`.
3. Created `.env` (Neo4j password from compose; Voyage key initially blank) + `.gitignore`.
4. `memoryschema neo4j deploy` — pulled image, started container.
5. `memoryschema neo4j schema` (with `NEO4J_PASSWORD` exported) — created 9 indexes.
6. `memoryschema hook install` — registered PostToolUse + Stop hooks → then **patched** (Issues M5–M7).
7. Wrote 4 seed entities; `memoryschema index --embed` (after Voyage key); `associations --recompute`.
8. Loaded Voyage key into `.env`; verified `voyage status`; embedded; `migrate neo4j-to-jsonl`.
9. Patched the hook for self-sufficiency; verified end-to-end (real Write-tool → auto-embed).

## 3. Final state (healthy)

- `memoryschema doctor`: **21/22** checks pass (the 1 failure is the package's own pytest suite — see M12).
- Backend `Neo4jMemoryStore`, **4 nodes**, 9 indexes, JSONL in sync (4 entries), Voyage embed OK (0.89s).
- Semantic recall verified (e.g. "which chart scale for journaling" → `chart-selection-criteria` @ 0.738).
- Live PostToolUse hook auto-embeds memory writes with **no manual indexing** (verified, see M6/M7).

---

## 4. Issues encountered & fixes

Severity key: **BLOCKER** (setup cannot proceed / silent data loss), **HIGH** (feature broken, workaround
exists), **MED** (degraded), **LOW** (cosmetic). "Upstream" = recommended package fix.

### Summary table

| # | Severity | Area | One-line |
|---|----------|------|----------|
| M1 | BLOCKER | CLI / Windows | Every CLI command crashes with `UnicodeEncodeError` (cp1252 vs `→`) |
| M2 | LOW | CLI / UX | `--project` rejected on `init` (it's a global flag; help example is misleading) |
| M3 | HIGH | Neo4j deploy | `deploy` schema/verify step fails auth — doesn't use the password it just generated |
| M4 | LOW | Neo4j schema | Deprecated `db.index.vector.createNodeIndex` Cypher |
| M5 | BLOCKER | Hook install / Windows | Hook command not shell-quoted → bash syntax error on every Write/Edit |
| M6 | BLOCKER | Hook / Windows | Hook silently skips ALL memory writes (backslash path never matches `/memory/`) |
| M7 | HIGH | Hook / env | Hook not self-sufficient — no `VOYAGE_API_KEY`/`NEO4J_PASSWORD` in Claude Code's hook env |
| M8 | MED | Store layers | `store.jsonl` never created with Neo4j backend; `embed --all` then `FileNotFoundError` |
| M9 | (expected) | Embeddings | Voyage key absent at init → semantic recall empty until provided |
| M10 | (notes) | Debugging | Five diagnostic pitfalls that produced false negatives during verification |
| M11 | LOW | CLI | `neo4j shell "<cypher>"` rejects an inline query argument |
| M12 | LOW | Dev env | `doctor` reports package pytest suite failing (irrelevant to runtime) |
| M13 | POLICY | Chain lifecycle | Default releases the chain between sessions (store read-only); operator requires an always-active chain |
| M14 | HIGH | Parser / write-gate | Unescaped `<` in observation text passes the write gate, then silently **truncates** the store via strict XML parse (Rule 5 documented but unenforced) — *see §10* |
| M15 | MED | Upsert / sync | Append-only chain accumulates stale observation variants; `sync` misses observation-level drift; no non-destructive resync — *see §10* |

---

### M1 — CLI crashes on Windows console encoding (BLOCKER)

**Symptom:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '→' in position 1686:
character maps to <undefined>
```
on `memoryschema --help` (and any command emitting the `→` arrow in help/usage text).

**Root cause:** The CLI writes Unicode (e.g. `→`) to stdout; the default Windows console encoding is
cp1252, which can't encode it. Click/rich output isn't forced to UTF-8.

**Fix (applied):** `export PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` before every invocation. Baked
into the project `.env`, into `CLAUDE.md`, and recorded as standing guidance.

**Upstream recommendation:** In the CLI entrypoint, call `sys.stdout.reconfigure(encoding="utf-8")` /
`sys.stderr.reconfigure(...)` on Windows (or set Click to ASCII-safe output). A first-run env check could
also warn. This blocks *everything* on a stock Windows Python — high priority for cross-platform support.

### M2 — `--project` not accepted on the `init` subcommand (LOW)

**Symptom:** `memoryschema init --project trading-journal …` → `Error: No such option '--project'.`

**Root cause:** `--project` is a **global** option (`memoryschema [--project X] COMMAND`), but the
`init --help` example reads `memoryschema init --project my-project --with-neo4j`, which is misleading.

**Fix (applied):** `memoryschema --project trading-journal init --scopes working,corpus`.

**Upstream recommendation:** Either accept `--project` on `init` too, or correct the `init --help` example.

### M3 — `neo4j deploy` fails its own schema/verify with auth error (HIGH)

**Symptom:** Container started, then:
```
Warning: Schema creation failed: {neo4j_code: Neo.ClientError.Security.Unauthorized}
  {message: Unsupported authentication token, missing key `credentials`}
Warning: Verification failed: Neo4j auth failed at bolt://localhost:7687.
  Set NEO4J_PASSWORD env var or check memoryschema.toml [neo4j] section.
```

**Root cause:** `deploy` generates a random password and writes it into `docker-compose.yml`
(`NEO4J_AUTH=neo4j/<pw>`), but its subsequent schema-creation / verification steps connect **without**
that password — they read `NEO4J_PASSWORD` from the environment, which isn't set, and the deploy never
exports or re-reads the password it just generated.

**Fix (applied):** Exported `NEO4J_PASSWORD=<value from docker-compose.yml>` and ran
`memoryschema neo4j schema` once the container was healthy. Then persisted the password in `.env`.

**Upstream recommendation:** `deploy` should reuse the password it just wrote — parse it back out of the
generated compose file, or write `.env` and load it — so the schema/verify steps authenticate. As-is,
`deploy` *looks* like it failed on a fresh setup.

### M4 — Deprecated vector-index Cypher (LOW)

**Symptom:**
```
db.index.vector.createNodeIndex is deprecated. It is replaced by CREATE VECTOR INDEX.
```
**Root cause:** Old Cypher syntax against Neo4j 5.26. **Fix:** none required — 9 indexes were created
successfully. **Upstream:** migrate to `CREATE VECTOR INDEX` to silence the warning and stay future-proof.

### M5 — Hook command not shell-quoted → breaks on spaced/backslash path (BLOCKER on Windows)

**Symptom:** After `memoryschema hook install`, **every** subsequent Write/Edit raised:
```
/usr/bin/bash: -c: line 1: syntax error near unexpected token `('
bash R:\Program Files (x86)\IG MetaTrader 4 Terminal - Live\packages\…\hook-post-write.sh C:\Python\…
```
Also `memoryschema hook status` reported `Script: MISSING`.

**Root cause:** `hook install` wrote an **unquoted** command with backslashes and spaces into
`~/.claude/settings.json`:
`bash R:\Program Files (x86)\…\hook-post-write.sh C:\Python\Python313\python.exe`. Git Bash word-splits
on the spaces and chokes on `(x86)`. The `hook status` "MISSING" was the same parser failing to locate
the script in the unquoted string.

**Fix (applied):** Edited both hook commands in `settings.json` to quote and forward-slash the paths:
```
bash "R:/Program Files (x86)/…/hook-post-write.sh" "C:/Python/Python313/python.exe"
```

**Upstream recommendation:** `hook install` MUST emit shell-quoted, forward-slashed paths (critical for
any install path containing spaces — extremely common on Windows: `Program Files`, `Program Files (x86)`).

### M6 — Hook silently skips ALL memory writes on Windows (BLOCKER)

**Symptom:** Writing `memory/*.md` via the editor's Write tool did not index anything (node count
unchanged); the hook exited 0 with no error. Auto-indexing simply never happened.

**Root cause:** The hook's gate checks use forward-slash patterns:
```bash
if [[ "$FILE_PATH" != *"/memory/"* ]] || [[ "$FILE_PATH" != *.md ]]; then exit 0; fi
```
On Windows, Claude Code passes a **backslash** `file_path` (`…\memory\foo.md`), so `*"/memory/"*` never
matches and the hook early-exits as if the file were a non-memory write. (The inner Python normalizes
backslashes, but the bash guard runs first and bails before reaching it.)

**Fix (applied):** Normalize at the top of the bash logic, before the guards:
```bash
FILE_PATH="${FILE_PATH//\\//}"
```

**Upstream recommendation:** Ship this normalization. This is the single most important Windows fix — it
makes auto-indexing silently inert otherwise, which is worse than a loud failure.

### M7 — Hook not self-sufficient: no credentials in the hook environment (HIGH)

**Symptom:** Even once the path matched (M6), the hook would upsert the node to Neo4j but **not embed**
it (and sometimes not reach Neo4j either) — because Claude Code's hook subprocess doesn't carry the
operator's exported `VOYAGE_API_KEY` / `NEO4J_PASSWORD`.

**Root cause:** The hook relied on those being present in the environment. They're only in the project
`.env`, which the hook didn't read.

**Fix (applied, requested by operator):** The hook now derives the project root (the path component
before `/memory/`) and loads that project's `.env` with a safe parser (skips comments/blank lines,
strips `export `/inline comments, does **not** `eval` values), exporting the credentials before running
the indexer:
```bash
ENV_FILE="${FILE_PATH%%/memory/*}/.env"
if [ -f "$ENV_FILE" ]; then
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in ''|'#'*) continue ;; esac
    _line="${_line#export }"
    case "$_line" in *=*)
      _key="${_line%%=*}"; _val="${_line#*=}"
      _key="${_key//[[:space:]]/}"; _val="${_val%%[[:space:]]#*}"
      [ -n "$_key" ] && export "$_key=$_val" ;;
    esac
  done < "$ENV_FILE"
fi
```

**Verification:** With a clean shell (no exports) and valid Claude-style JSON, the hook self-loaded
`.env`, embedded (1024 dims in Neo4j), and a real Write-tool call round-tripped: probe entity returned
as the top semantic recall hit (0.605). Auto-embed now works with no manual `index --embed`.

**Upstream recommendation:** Load the project `.env` in the hook (or have `MemoryConfig` read it). Both
M6 and M7 are edits to the shared package hook `src/memoryschema/hooks/hook-post-write.sh`, so
`memoryschema hook upgrade` would overwrite them — they should be merged upstream rather than carried as
local patches.

### M8 — `store.jsonl` never created with Neo4j backend; `embed --all` then fails (MED)

**Symptom:** `doctor` → `✗ store_jsonl  store.jsonl not found`. `memoryschema embed --all` →
`FileNotFoundError: …\memory\store.jsonl`.

**Root cause:** With the Neo4j backend active, `index` / `write` persisted only to Neo4j; the JSONL L1b
layer was never materialized. But `embed`/`reembed` read from `store.jsonl`, so they can't run.

**Fix (applied):** Used `memoryschema index --embed` (operates against the live store) to embed, and
`memoryschema migrate neo4j-to-jsonl` to materialize/sync the JSONL fallback. Re-running `sync` confirms
`in sync (4 ↔ 4)` and `doctor` then shows `✓ store_jsonl (4 entries)`.

**Upstream recommendation:** Either have `index`/`write` always persist JSONL alongside Neo4j (so the
documented L0→L1a→L1b→L2 degradation chain actually exists after a normal write), or make `embed` source
from the active backend, or have `doctor` treat "Neo4j present, JSONL absent" as OK rather than a failure.

### M9 — Voyage key absent at init (expected setup step)

**Symptom:** `voyage status` → `API key: NOT SET`; `memoryschema recall` returned `No results found`
(semantic path needs query embeddings), while keyword `search` worked.

**Root cause / fix:** Key not yet provided. Found it in `VoyageAIKey.txt` at the terminal root, added to
`.env`, ran `index --embed`, verified recall. Documented so future deployments know recall is keyword-only
until the key is set.

### M10 — Diagnostic pitfalls (false negatives during verification)

Recorded because they cost real debugging time and are likely to recur for anyone validating the hook:

1. **Hand-built JSON with single backslashes.** A test payload `{"file_path":"R:\Program…"}` built in
   bash is **invalid JSON** (`\P` etc.); the hook's `json.load` throws, is suppressed by `2>/dev/null`,
   `tool_name` comes back empty, and the hook exits as a non-Write call. Generate fixtures with
   `json.dumps` so backslashes are doubled.
2. **`/tmp` on Windows Python.** Writing a fixture to `/tmp/…` fails — Windows Python doesn't resolve the
   Git Bash mount. Use a CWD-relative temp file.
3. **`get --json` omits the embedding vector.** Verifying via `get` showed `embedding: NONE` even when an
   embedding existed. Verify with a direct `Neo4jMemoryStore().get(name)["embedding"]` length, or via a
   semantic recall hit.
4. **Low-importance entities rank low even when embedded.** A probe with `importance=2` didn't appear in
   top-N recall despite a valid embedding (importance is 30% of score). Don't use recall ranking alone as
   proof of embedding; check vector dims directly.
5. **The Write tool itself fires the live hook.** Creating a memory file via the editor triggers the
   PostToolUse hook; doing that *and* invoking the hook manually double-processes the file and can produce
   confusing "already exists / read-only" states (the auth gate makes non-active-chain entities read-only
   once present). Test the manual hook against a file created out-of-band (e.g. via shell `cat >`).

### M11 — `neo4j shell` rejects an inline Cypher argument (LOW)

**Symptom:** `memoryschema neo4j shell "MATCH (m) RETURN m"` → `Error: Got unexpected extra argument (…)`.
**Fix:** Queried via Python (`Neo4jMemoryStore().get(...)`). **Upstream:** accept an inline query arg, or
document that `shell` is interactive-only.

### M12 — `doctor` reports the package pytest suite failing (LOW, dev-env only)

**Symptom:** `✗ tests  exit code 1`. **Root cause:** the **package's own** dev test suite (`pytest tests/`)
fails in this environment (not set up for package development). **Impact:** none on the runtime store.
**Upstream:** consider scoping the `doctor` "tests" check to dev installs, or making it informational.

### M13 — Always-active-chain policy (POLICY / UX finding)

**Context:** The default working-memory guideline is "one chain per session, released when concluded."
After release, `chain status` reports *"No active chain (all memories read-only)"* and the write loop is
silently inactive until a new chain is started — so between sessions (and after any `release`) the memory
system captures nothing.

**Operator directive:** keep a chain active **at all times** — never sit in the released/read-only state.

**Fix (applied):**
1. Started a rolling working chain `chain-session-2026-06-21` (entity `memory/chain-session-2026-06-21.md`).
2. Codified the policy in the project `CLAUDE.md` (memory-backend section): at session start run
   `memoryschema chain status`; if none active, start one; when a chain is concluded, append a
   `Conclusion:` observation, `release`, then **immediately start its successor**.
3. Recorded a cross-session working-preference memory (`keep-chain-active`) in the editor's per-project
   memory so the policy surfaces via recall even when not operating inside the vault.

**Mechanics / caveat:** Only one chain can be authorised at a time, so "always active" is implemented as
"never leave the released state" — release-then-immediately-start. Naming convention:
`chain-session-<YYYY-MM-DD>` for general work, topic-named chains for specific investigations.

**Upstream recommendation (for memory development):** Consider an opt-in "persistent chain" mode — e.g. a
config flag (`always_active_chain = true`) or a CLI helper (`chain rotate <new-name>` that releases the
current chain and starts a successor atomically), and have the Stop hook auto-start a session chain if
none is active. The current default (read-only between sessions) is a reasonable safe default, but several
workflows want continuous capture; first-class support would avoid the manual release→start dance.

---

## 5. Residual / known items

- **Secrets:** *(resolved 2026-06-21)* the root `VoyageAIKey.txt` plaintext copy was deleted; the
  gitignored `.env` is now the single source of the Voyage key. The Neo4j password still lives in
  `docker-compose.yml` (committed-by-default) and `.env` — acceptable for a local single-user dev DB.
- **Package edits committed** *(2026-06-21)* on branch `fix/windows-port-and-eval-residuals` (4 commits:
  hook Windows fixes, eval fixes E1/E2/E3 + tests, test portability, this report). Not pushed. This
  persists the M6/M7 hook patches against `hook upgrade`/reinstall; still merge upstream so future
  package versions carry them.
- **Two hook copies — now synced.** The M6/M7 fixes were applied to both
  `src/memoryschema/hooks/hook-post-write.sh` (the copy the live `~/.claude/settings.json` hook invokes)
  and the plugin-distribution copy `.claude-plugin/hooks/hook-post-write.sh` (synced 2026-06-21; the two
  are now byte-identical modulo line endings, syntax-checked). Keep them in sync on future edits — ideally
  generate one from the other so they cannot drift.
- **JSONL must be resynced** (`migrate neo4j-to-jsonl`) after bulk CLI mutations to keep the fallback
  layer current (M8).
- **An active chain must always exist** (M13) — on `release`, immediately start a successor. Current
  holder: `chain-session-2026-06-21`.

## 6. Prioritized upstream recommendations (for memory development)

1. **(BLOCKER, Windows)** Force UTF-8 stdout in the CLI entrypoint (M1).
2. **(BLOCKER, Windows)** Normalize backslash paths in the hook before the `/memory/` guard (M6).
3. **(BLOCKER, Windows)** Shell-quote + forward-slash paths in `hook install` (M5).
4. **(HIGH)** Make `neo4j deploy` use the password it generates for its own schema/verify (M3).
5. **(HIGH)** Load project `.env` in the hook so it's self-sufficient (M7).
6. **(MED)** Persist JSONL on normal writes, or fix `embed` to read the active backend (M8).
7. **(LOW)** Fix `init --help` `--project` example (M2); update vector-index Cypher (M4); accept inline
   `neo4j shell` query (M11); scope the `doctor` tests check (M12).
8. **(POLICY)** Offer a persistent-chain mode — `always_active_chain` config flag and/or an atomic
   `chain rotate <new-name>`, with the Stop hook auto-starting a session chain if none is active (M13).
9. **(HIGH)** Enforce Rule 5 at the write gate and harden the parser (M14): add a validator check that
   **rejects or auto-escapes** unescaped `<`/`&` in text fields, and make the observation parser **fail
   loudly / report "parsed N of M"** instead of silently truncating on the first malformed node (ideally
   parse each `<memory:observation>` independently so one bad node can't drop its siblings).
10. **(MED)** Close the resync/drift gap (M15): add `reconcile <name>` to rebuild an entity's observations
    from its canonical `.md` **while preserving graph-only relations/associations**, and extend
    `sync`/`status` to detect **observation-level** drift (store ⊋ file), not just entity presence.

**Theme:** the package works well once configured, but had **not been hardened for Windows** — the three
blockers (M1, M5, M6) are all Windows path/encoding issues that make the system silently or loudly fail
on a stock Windows + Git Bash + spaced install path. Fixing those three would make a clean Windows
install work end-to-end without manual intervention.

---

## 7. System evaluation (2026-06-21)

Run live against the deployed system after setup. **Verdict: functionally healthy and working; retrieval
is strong at the top rank; the real weaknesses are observability and small-corpus immaturity, not data
integrity.**

### Method
- `memoryschema eval --mode retrieval` (synthetic fixtures — algorithm quality, corpus-independent).
- `memoryschema eval --mode salience` (write-decision quality).
- A 5-query real-corpus recall battery (query → expected top-1 entity).
- Direct Neo4j inspection of nodes/edges; per-entity embedding-coverage check.

### Scorecard

| Dimension | Result | Grade |
|-----------|--------|-------|
| Operational health | `doctor` 21/22; Neo4j healthy; JSONL in sync | Strong |
| Embedding coverage | 5/5 entities embedded (1024-dim); Voyage 0.89s | Strong |
| Retrieval algorithm (synthetic) | MRR **1.000**, nDCG@10 0.611, recall@5 0.479, superseded-exclusion 1.0 | Good |
| Real-corpus recall | 3/5 top-1 hits; 2 near-misses (correct entity ranked #2) | Fair |
| Graph layer (Neo4j) | 23 edges: 2 USES, 1 INFORMS, 20 ASSOCIATED_WITH — correct | Working |
| CLI observability | `associations` / `get` read JSONL → under-report (0 / none) | Weak |
| Salience eval | reports only baseline/perfect bounds, no measured score | Incomplete |
| Auto-capture | hook self-sufficient, auto-embeds on Write (verified) | Strong |

### Synthetic retrieval detail
```
Broad semantic        recall@5=0.30  mrr=1.00  ndcg@10=0.47
Scoped episodic       recall@5=0.30  mrr=1.00  ndcg@10=0.47
Procedural            recall@5=0.38  mrr=1.00  ndcg@10=0.54
User-provenance       recall@5=0.60  mrr=1.00  ndcg@10=0.72
Ingested (rank below) recall@5=0.30  mrr=1.00  ndcg@10=0.47
Superseded (exclude)  recall@5=1.00  mrr=1.00  ndcg@10=1.00
Averages              recall@5=0.479 mrr=1.000 ndcg@10=0.611
```

### Real-corpus battery
| Query | Top-1 returned | Score | Verdict |
|-------|----------------|-------|---------|
| which chart scale should I use | chart-selection-criteria | 0.704 | PASS |
| what happened in the market on the 19th | chart-selection-criteria | 0.545 | MISS (usd-strength-20260619 was #2) |
| how is the journal wiki structured | chain-init-trading-journal | 0.666 | MISS (trading-journal-overview was #2) |
| how was the memory system set up | chain-init-trading-journal | 0.613 | PASS |
| policy for keeping memory authorised | chain-session-2026-06-21 | 0.607 | PASS |

### Strengths
- **Top-rank retrieval excellent** — MRR 1.000; relevant entity ranks #1 when present. Superseded
  exclusion perfect.
- **Graph is real and correct** — Neo4j holds the authored typed relations plus 20 k-NN association
  edges; cascade infrastructure exists.
- **All storage layers intact; write path self-sufficient** (post-M6/M7).

### Weaknesses & evaluation findings
- **E1 (observability, ties to M8):** `memoryschema associations` reports *0 edges* and `get` shows no
  relations, while Neo4j actually holds **23 edges**. The CLI reads the JSONL store (regenerated by
  `migrate` without association data) instead of the live Neo4j backend. Data is intact; the *reporting*
  is wrong. **Upstream:** point read-side CLI commands at the active backend, or persist associations into
  JSONL on recompute.
- **E2 (salience eval is a no-op):** `eval --mode salience` prints only baseline (f1 0.667) and perfect
  (1.0) reference points — never the system's measured precision/recall. Write-salience quality is
  currently unmeasured. **Upstream:** emit the measured score.
- **E3 (importance weighting beats close matches):** both real-corpus misses lost on the 30% importance
  term, not relevance. For a journaling workload (freshest/most-relevant note wins), consider tuning the
  semantic weights (default rel 0.5 / imp 0.3 / rec 0.2) toward relevance + recency.
- **E4 (small corpus):** 5 entities — metrics are indicative, not conclusive (recall@5 == recall@10 means
  ≤5 candidates). Re-evaluate after ~20–30 journaled days for statistically meaningful recall@k / nDCG.

### Recommendations
1. Tune retrieval weights for journaling (raise relevance/recency); re-run the battery (E3).
2. Treat `associations` / `get` CLI output as unreliable; verify the graph via Neo4j until fixed (E1/M8).
3. Make the salience eval emit a measured score before trusting it (E2).
4. Re-evaluate after the corpus reaches ~20–30 entities (E4).

**Bottom line:** storage, embeddings, core retrieval, and the knowledge graph are sound and working; the
gaps are in *self-reporting tooling* and *corpus size*, both addressable.

---

## 8. Fixes implemented (2026-06-21)

E1, E2, E3 were fixed in the package; E4 is operational (accumulate corpus). All changes are minimal and
reuse existing patterns. **717 passed, 2 failed** in the suite — the 2 failures are pre-existing
Windows-path assumptions in `test_config.py::test_store_path_override` (asserts a Unix `/custom/...` path
that Windows resolves to `C:\custom\...`) and `test_inheritance.py::test_nested_two_levels` (forward-slash
substring vs backslash path), in test files not touched by these fixes. 12 new tests added
(`tests/test_eval_weakness_fixes.py`), all green.

**E1 — observability (FIXED).** `Neo4jMemoryStore.list_all()` now mirrors `get()`: it collects
`relations`/`backlinks`/`associations` via `OPTIONAL MATCH` and maps with `_record_to_dict`. This repairs
the `associations` CLI (now `5 entries / 20 edges`, was `0/0`) and `migrate neo4j-to-jsonl` (JSONL now
carries associations, restoring the fallback layer). The `get` CLI also now prints relations/backlinks/
associations. Files: `neo4j_store.py:list_all`, `cli/memory_cmd.py:get`.

**E2 — salience measurement (FIXED).** Added a deterministic, policy-grounded heuristic
`eval/salience_scorer.py:classify_salience` and wired a measured `System (heuristic)` row into
`cli/eval_cmd.py:_run_salience_eval`. Result on the 20 fixtures: **precision 1.000, recall 0.900,
f1 0.947** — a real, improvable point between baseline (0.667) and perfect (1.0), explicitly labelled a
coded proxy (not the LLM).

**E3 — configurable weights (FIXED).** Score-blend weights are now config-driven: new
`MemoryConfig.semantic_weights` / `structured_weights`, TOML keys in `inheritance.py`, a shared
`store._resolve_weights()` helper read by both stores' `_score_entry`, and `get_store` passes `config` to
both backends. The project `memoryschema.toml` sets `[retrieval] semantic_weights = [0.15, 0.15, 0.70]`.
The recall battery improved **3/5 → 4/5**: "what happened on the 19th" now correctly returns
`usd-strength-20260619`. The remaining miss ("how is the wiki structured" → `chain-init`) is now a genuine
embedding judgment (relevance dominant at 0.70; chain-init's description contains "wiki"), not a weighting
artifact.

**E4 — corpus size (operational).** No code change; re-evaluate after ~20–30 journaled entities.

**New findings during implementation (for memory development):**
- **M12 root cause confirmed:** `doctor`'s "tests" failure was simply `pytest` not installed (only the
  `[all]` extra was installed, not `[dev]`). Installing pytest, the suite runs (717 pass).
- **Test isolation gap:** running `pytest` with `NEO4J_PASSWORD`/`VOYAGE_API_KEY` exported causes
  `get_store()`-based tests to write to the *live* Neo4j (observed: stray `test` and `imported` nodes
  polluting the trading-journal store; cleaned up). Recommend the suite force a temp/JSONL store (or a
  dedicated test DB) regardless of ambient env, and that `doctor` run tests in an isolated store.

---

## 9. Post-fix re-evaluation & residual closures (2026-06-21)

### Re-evaluation vs the §7 baseline

| Dimension | §7 (pre-fix) | Post-fix | Δ |
|-----------|--------------|----------|---|
| CLI observability | Weak — `associations` showed 0 | **Strong** — 5 entries / 20 edges; `get` shows relations | ▲ E1 |
| Salience eval | Incomplete — no measured row | **Measured** — System f1 **0.947** (rec 0.9) | ▲ E2 |
| Real-corpus recall | 3/5 top-1 | **4/5 top-1** | ▲ E3 |
| Retrieval algorithm (synthetic) | MRR 1.000, nDCG 0.611, recall@5 0.479 | unchanged | — |
| Operational health (`doctor`) | 21/22 | **22/22** | ▲ R1 |

The synthetic numbers are unchanged by design: the synthetic eval builds a store with **default** weights
(not the project tuning), and `recall@5 == recall@10` reflects the small fixture set (E4). The single
remaining real-corpus miss ("how is the wiki structured" → `chain-init`) is a **genuine embedding
judgment** (relevance dominant at 0.70; `chain-init`'s description contains "wiki"), not a weighting bug.

### Residuals closed
- **R1 — Windows test failures (FIXED).** Both were test-only Unix-path assumptions; production code
  unchanged. `test_config.py::test_store_path_override` → uses `tmp_path`; `test_inheritance.py::
  test_nested_two_levels` → uses `p.as_posix().endswith(...)`. Result: **719 passed / 0 failed**, `doctor`
  **22/22**. (Four other `str(path)` substring assertions were intentionally left as-is — they match bare
  directory names, which is already OS-portable.)
- **R4 — secrets consolidated (FIXED).** Deleted root `VoyageAIKey.txt`; the gitignored `.env` is the
  single source of the Voyage key. `voyage status` still OK.
- **R5 — edits persisted (DONE, local).** Committed on branch `fix/windows-port-and-eval-residuals`
  (commits: ① hook Windows fixes; ② eval fixes E1/E2/E3 + tests; ③ test portability; ④ this report;
  ⑤ residual-closure doc). **Not pushed** — pushing is outward-facing and was out of the approved plan's
  scope; awaiting explicit go-ahead. PR (when ready, browser — `gh` not installed):
  `https://github.com/shehzadqayum/memory-schema/compare/main...fix/windows-port-and-eval-residuals`.
- **R3 — recall miss (ACCEPTED).** Legitimate embedding judgment; re-assess as the corpus grows. Tuning a
  5-entity corpus to flip one query would overfit.
- **E4 — corpus size (OPERATIONAL).** Per decision, no synthetic-eval depth knob (BM25 fallback limits its
  value). Grow the corpus by journaling; re-run `eval --store memory/store.jsonl` + the recall battery at
  ~20–30 entities for a conclusive verdict.

### Still open (transparency)
- **Test-isolation gap** (§8) — unfixed upstream; mitigate by running `pytest` without `NEO4J_PASSWORD`,
  or fix the suite to force a temp store.
- **Local-only until pushed** — the branch must be pushed/merged so future package versions carry the
  Windows + eval fixes (otherwise `hook upgrade`/reinstall from upstream reintroduces the bugs).

---

## 10. Continued-use findings (2026-06-22)

Surfaced while the journal was in active use — building the periodic (day/week/month) performance reports.
Both are **read/observability-layer integrity** issues (the same class as E1): the markdown file on disk is
correct, but the *store* under- or over-represents it, silently. Neither blocks the journal; both are real
package defects worth fixing upstream.

### M14 — Unescaped `<` in observation text silently truncates the store (HIGH, data integrity)

**Symptom.** `memoryschema get chain-session-2026-06-21` reported **25 observations** while the canonical
`.md` file contained **30** (Steps 1–30). A strict-XML sanity parse failed with `expat: mismatched tag`.
Steps 25–30 were invisible to every strict-parse consumer (the `get` count, and any non-regex reader).

**Root cause.** An observation written by the LLM in an earlier session contained the literal placeholder
text `<date>` (in `…as separate files <date>_day_grid_s4.png…`). Per **schema Rule 5** the `<` MUST be
XML-escaped — but:
1. the **write gate did not reject it**: the PostToolUse hook parsed, embedded, and indexed the file
   without complaint (Rule 5 is documented but **unenforced** by the V1–V12 validator); and
2. downstream, any **strict XML** reader treats `<date>` as an unclosed tag → `mismatched tag` → the
   `<memory:observations>` block **truncates at that node**, silently dropping every later observation.

The lenient/regex code paths (the hook indexer, `recall`) still saw the raw text, which is why the file kept
accumulating and `sync` looked healthy — masking the loss from strict consumers. This is the same failure
class as **E1**: *the system under-reports its own state*, here triggered by one un-escaped character.

**Why it matters.** Silent data loss at the read layer with a correct file on disk. Any long-lived chain
that ever emits a raw `<` (very likely — LLMs write `<placeholder>`, `a<b`, generics, etc.) loses its tail
to strict consumers until the offending character is escaped, with **no error surfaced**.

**Fix applied (data).** Escaped `<date>` → `&lt;date&gt;` in the observation. The store then parsed all
30 observations and the strict XML check passed.

**Upstream recommendations.**
- **M14a (HIGH)** — *Enforce Rule 5 at the write gate.* Add a validator check (e.g. V13) that **rejects or
  auto-escapes** a raw `<`/`&` not opening a known `memory:` tag in `description`/`observation`/`reasoning`/
  `prompt`/`chain`. Blocking at write time prevents the corruption at source.
- **M14b (HIGH)** — *Parser robustness.* A strict parse that meets malformed content must **fail loudly or
  emit "parsed N of M observations"**, never silently truncate. Ideally parse each `<memory:observation>`
  independently so one bad node cannot drop its siblings.
- **M14c (MED)** — *Drift check.* `doctor`/`status` should compare **per-entity file-observation-count vs
  store-observation-count** and flag mismatches — one check catches both this truncation (store < file) and
  the stale accumulation in M15 (store > file).

### M15 — Append-only chain accumulates stale observation variants; no non-destructive resync (MED)

**Symptom.** After fixing M14, the store reported **31** observations for the **30**-observation file. Two
were **stale** older wordings — an earlier phrasing of Step 16 (pre-existing across prior sessions) and the
pre-escape raw-`<date>` Step 25 (superseded by the escaped version). `sync` still reported **"in sync."**

**Root cause.** **Rule 6** upsert appends observations and skips only **exact** duplicates. Whenever an
observation is reworded across sessions — normal for an evolving chain — the prior wording stays in the
graph permanently, so the store's observation set monotonically **supersets** the canonical `.md`. The
strict-parse truncation in M14 had been *hiding* this accumulation (the count was capped at 25); escaping
the `<` revealed the true accumulated state.

**Why it isn't trivially fixable.** `memoryschema delete <name>` removes the entity from **all stores + the
`.md` file + its accumulated graph-only relations**. A long-lived chain's `USES` edges to evidence memories
live in the graph (merged over sessions), **not** in the `.md` file — so a delete+reindex rebuild would
discard them. There is **no non-destructive "rebuild this entity's observations from its file"** path. We
therefore **left the 2 benign variants** rather than damage the relation graph for a cosmetic dedup.

**Upstream recommendations.**
- **M15a (MED)** — Add `reconcile <name>` (or `resync`) that rebuilds an entity's observations/description/
  reasoning from its canonical `.md` **while preserving** graph-only relations/associations. For the
  authorized chain, an opt-in "replace-observations-from-file" merge mode would also resolve it.
- **M15b (MED)** — Extend `sync`/`status` to detect **observation-level** drift (store ⊋ file), not just
  entity presence — today a 31-vs-30 divergence reports clean.
- **M15c (LOW)** — Optionally normalize whitespace before the exact-duplicate check so trivially-reworded
  variants don't accumulate (true rewordings remain distinct, so M15a is the real fix).

**Net:** the journal's data is intact (the `.md` files are canonical and now strict-XML-valid; the store is
in sync at the entity level). M14 is the priority — it is silent, easily triggered, and a one-line validator
rule would prevent it.
