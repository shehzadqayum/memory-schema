# Memory System — Technical Reference

## Overview

**Schema:** `docs/schema.md` (source of truth, v4)
**Guidelines:** `.claude/rules/memory-*.md` (per-scope usage)
**Embedding model:** Voyage AI `voyage-4-lite` (1024 dimensions)
**Primary store:** Neo4j (L2b, optional)
**Fallback store:** `memory/store.jsonl` (L1b)
**Access:** `get_store()` — Neo4j first, JSONL fallback
**CLI:** `memoryschema` (pip install memory-schema)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  L0: MEMORY.md (always in context, auto-updated by hook) │
├─────────────────────────────────────────────────────────┤
│  L1a: Markdown files (git-tracked, human-readable)       │
├─────────────────────────────────────────────────────────┤
│  L1b: JSONL store (structured, machine-readable)         │
├─────────────────────────────────────────────────────────┤
│  L2a: Voyage embeddings (1024-dim per entry)             │
├─────────────────────────────────────────────────────────┤
│  L2b: Neo4j (vector k-NN, graph traversal, associations) │
└─────────────────────────────────────────────────────────┘
```

Each layer adds capability without being required. The system degrades gracefully.

**Compact resilience:** The PostToolUse hook auto-appends working memory entries to MEMORY.md on write.

---

## Entity Structure (Schema v4)

```xml
<memory:entity schema="4" name="unique-identifier" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation>Atomic fact</memory:observation>
  </memory:observations>
  <memory:prompt>User input that triggered this memory</memory:prompt>
  <memory:reasoning>Narrative thinking — why, alternatives, connections</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
</memory:entity>
```

**Required:** schema, name, description.
**Optional:** importance (default 5), confidence (1-10), type (free-form), observations, reasoning, prompt, chain, relations, project.
**Server-managed:** status, embedding, embeddings, divergence_profile, created_at, last_accessed, access_count, backlinks, associations.

---

## Type System

| Type | Use |
|------|-----|
| Free-form | LLM determines best value. Scoring recognises `semantic`, `episodic`, `procedural` for recency modifiers. |
| `procedural` | Validated approaches, feedback |

---

## Retrieval

### Scoring Formula

```
score = recency(0.995^hours) × 0.2 + importance/10 × 0.3 + cosine_similarity × 0.5
```

**Type factor** (applied to base recency before weighting):
- `semantic`: `max(recency, 0.6)` — facts never fully decay
- `episodic`: standard `0.995^hours` — events age naturally
- `procedural`: `recency^(1/(1 + 0.3*min(access_count, 10)))` — access-reinforced

**`confidence`** is write-time metadata only — captured for calibration analysis but does not affect retrieval scoring.

**Bonuses** (added after weighted sum, before clamping to 1.0):
- Hub bonus: `+0.05 * ln(1 + backlinks)` — log-scale, diminishing returns
- Text match: `+0.1` substring (Neo4j) or BM25 up to `+0.3` (JSONL)

**BM25 parameters** (JSONL store only): k1=1.2, b=0.75, avg_dl=50, whitespace tokenization, normalized to [0, 0.3] boost range.

**When no embedding available:** relevance weight redistributed — 40% to recency, 60% to importance.

**Numpy acceleration:** vectorized cosine similarity via numpy when installed, pure-Python fallback otherwise.

### Three-Channel Cascade

```
Vector k-NN seeds → explicit relations → backlinks → ASSOCIATED_WITH associations
```

---

## Pipeline

### Write Path

```
Response → memory entity (.md) → PostToolUse hook
  → parse (tags.py) → write gate (REJECT/QUARANTINE/ACCEPT)
  → embed (Voyage AI, non-blocking) → Neo4j upsert (or JSONL fallback)
  → single-node associations → L0 update
  → append to MEMORY.md → L0 budget enforcement (evict if over limit)
```

### Recall Path

```
Query → embed query → vector k-NN seeds → cascade BFS
  → relations + backlinks + associations → ranked results
```

---

## Hook Output Formats

Hooks communicate with Claude Code by printing JSON to stdout. The valid fields depend on the event type.

### Common Fields (all event types)

| Field | Type | Effect |
|-------|------|--------|
| `continue` | boolean | If `false`, abort the current operation |
| `suppressOutput` | boolean | Hide the hook's output from the user |
| `stopReason` | string | Reason shown when `continue: false` |
| `decision` | string | PreToolUse only: `"allow"`, `"deny"`, `"ask"` |
| `reason` | string | Explanation for the decision |
| `systemMessage` | string | Injected into Claude's context as a system message |

### Event-Specific: `hookSpecificOutput`

The `hookSpecificOutput` object (with `hookEventName` and `additionalContext`) is only valid for certain event types:

| Event Type | `hookSpecificOutput` supported? |
|------------|-------------------------------|
| PreToolUse | Yes |
| PostToolUse | Yes |
| UserPromptSubmit | Yes |
| **Stop** | **No** — use `systemMessage` instead |
| **SessionStart** | **No** |
| **PreCompact** | **No** |

> **Common mistake:** Using `hookSpecificOutput.additionalContext` in a Stop hook. Claude Code silently ignores this field for Stop events. Use `systemMessage` at the top level instead.

### Examples

**Stop hook (correct):**
```json
{"systemMessage": "Reminder: update the active chain entity."}
```

**Stop hook (WRONG — will be ignored):**
```json
{"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "..."}}
```

**PostToolUse hook (correct — either form works):**
```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}
```

---

## Audit Trail

All mutations and gate decisions are logged to `memory/audit.jsonl` (append-only, never truncated).

**Gate decision record:**
```json
{"timestamp": "2026-06-10T...", "operation": "gate_decision", "name": "entity-name", "verdict": "accept", "reasons": ["..."], }
```

**Mutation record:**
```json
{"timestamp": "2026-06-10T...", "operation": "upsert", "name": "entity-name", "changes": {"description": {"prior_hash": "a1b2c3...", "new_hash": "d4e5f6..."}}}
```

Tracked fields: description, type, status, importance, confidence, body, prompt, reasoning, chain, project. Audit failure is silently swallowed — never blocks mutations.

---

## Graceful Degradation

| Component | If unavailable | Behavior |
|-----------|---------------|----------|
| Neo4j | JSONL fallback | `get_store()` tries Neo4j, catches all exceptions, falls back silently |
| Voyage AI key | No embeddings | Entries indexed without vectors; keyword search only |
| Embedding failure | Non-blocking | Warning logged, entry saved unembedded |
| Concurrent writes | Advisory locking | `fcntl` on Unix (raises IOError on contention); no-op on Windows |
| Audit logging | Silently swallowed | Mutations proceed even if audit.jsonl write fails |

---

## Python API

```python
from memoryschema import (
    MemoryConfig, MemoryStore, get_store,
    parse_memory_file, parse_memory_content,
    validate, validate_file, validate_directory,
    discover_memory_files, consolidate,
)

# Optional (require extras)
from memoryschema import Neo4jMemoryStore, embed_text, embed_batch, rerank
```

### Key Classes

- `MemoryConfig` — configuration dataclass (env vars, paths, defaults)
- `MemoryStore` — JSONL-backed store (L1b)
- `Neo4jMemoryStore` — Neo4j-backed store (L2b, same interface)
- `get_store(config=None)` — factory, returns best available backend

---

## Scripts

| Module | Purpose |
|--------|---------|
| `memoryschema.tags` | Parse `<memory:entity>` XML (v2: prompt + reasoning) |
| `memoryschema.store` | JSONL store + `get_store()` factory |
| `memoryschema.neo4j_store` | Neo4j store (O(1) upsert, vector k-NN, graph) |
| `memoryschema.embeddings` | Voyage AI: embed_text, embed_batch, rerank |
| `memoryschema.validator` | Schema validation (V1-V11, R1-R7, F1, F3) |
| `memoryschema.schema` | Create Neo4j indexes and constraints |
| `memoryschema.consolidation` | Batch index un-indexed files |
| `memoryschema.migration` | JSONL ↔ Neo4j migration |
| `memoryschema.reembed` | Re-embed entries by prefix |
| `memoryschema.discovery` | Find .md files under a path |
| `memoryschema.config` | Centralized configuration + `from_toml()` factory |
| `memoryschema.hierarchy` | Dot-notation project hierarchy — see [hierarchy-and-inheritance.md](hierarchy-and-inheritance.md) for full API |
| `memoryschema.inheritance` | TOML config chain + rules resolution — see [hierarchy-and-inheritance.md](hierarchy-and-inheritance.md) for full API |
| `memoryschema.audit` | Append-only mutation log with field-level change tracking |
| `memoryschema.l0_budget` | MEMORY.md token budget enforcement with score-based eviction |
| `memoryschema.write_gate` | Three-verdict write gate: ACCEPT/REJECT/QUARANTINE pipeline |
| `memoryschema.cli._hooks_util` | Shared hook utilities: path resolution, settings I/O, registration/removal/upgrade, version detection, diagnostics, cross-project scan (HOOK_MATCHER, LEGACY_MATCHERS, HOOK_VERSION constants) |
| `memoryschema.numeric_probe` | Numeric contradiction detection: extract_claims, compare |
| `memoryschema.cli.eval_cmd` | Evaluation harness: recall@k, MRR, nDCG metrics |
| `memoryschema.cli.reflect_cmd` | Episodic clustering and semantic summary synthesis |

---

## CLI Commands

| Command | Category | Key flags | Description |
|---------|----------|-----------|-------------|
| `init` | Setup | `--with-neo4j`, `--scopes`, `--neo4j-password` | Initialize project (memory dir, TOML, rules, docker-compose) |
| `neo4j` | Setup | deploy, up, down, status, logs, schema, reset, shell | Manage Neo4j container |
| `voyage` | Setup | status, test | Manage Voyage AI connectivity |
| `status` | Operations | `--json` | Show store backend, node count, embedding coverage |
| `recall` | Operations | `--project`, `--include-inactive`, `--json`, `-n` | Semantic search with cascade recall |
| `get` | Operations | `--json` | Retrieve single entity by name |
| `list` | Operations | `--type`, `--project`, `--include-inactive`, `--json`, `-n` | List entities with filters |
| `write` | Operations | | Parse, validate, gate, embed, and index a memory file |
| `delete` | Operations | `--confirm` | Remove entity from all stores + MEMORY.md |
| `search` | Operations | `--type`, `--project`, `--include-inactive`, `--json`, `-n` | Full-text keyword search |
| `archive` | Lifecycle | | Set status=archived (exclude from default recall) |
| `unarchive` | Lifecycle | | Restore archived → active |
| `reactivate` | Lifecycle | | Restore superseded → active |
| `quarantine` | Lifecycle | list, review, release, reject `--confirm` | Review quarantined entries |
| `validate` | Quality | `--strict` (Q1-Q2, Q6-Q8), `--json` | Validate memory files against schema |
| `index` | Indexing | `--base-path`, `--project` | Batch index un-indexed files |
| `embed` | Indexing | `--prefix`, `--all`, `--batch-size`, `--coverage`, `--dry-run` | Re-embed entries |
| `associations` | Indexing | `--k`, `--recompute` | Show or recompute k-NN associations |
| `reflect` | Indexing | `--project`, `--min-cluster`, `--max-cluster`, `--dry-run`, `--json` | Cluster episodic → semantic summaries |
| `eval` | Quality | | Evaluation harness (recall@k, MRR, nDCG) |
| `migrate` | Data | `jsonl-to-neo4j --batch-size --skip-assoc`, `neo4j-to-jsonl --output` | Migrate between JSONL and Neo4j |
| `sync` | Data | | Reconcile JSONL and Neo4j stores |
| `backup` | Lifecycle | `--neo4j-only`, `--jsonl-only`, `--files-only` | Full or selective backup |
| `restore` | Lifecycle | | Restore from backup archive |
| `reset` | Lifecycle | `--confirm`, `--neo4j-only`, `--store-only`, `--working-memory-only` | Wipe data (full or selective) |
| `clean` | Lifecycle | `--confirm`, `--dry-run` | Complete removal of memory system |
| `export` | Data | `--format` (tar/jsonl/md), `--output` | Portable archive for moving to another project |
| `import` | Data | `--format` | Import from portable archive |
| `hook` | Hooks | install, uninstall, status `--json`, upgrade `--dry-run --per-project`, check `--json`, scan `--json --scan-dir`, test | Manage PostToolUse and Stop hooks (version tracking, upgrade, diagnostics, cross-project scan) |
| `force` | Audit | `--type`, `--target`, `--level` | Record typed force event (world-change) |
| `decline` | Audit | `--reason`, `--name-hint` | Record write decline (salience instrumentation) |
| `doctor` | Diagnostics | `--fix`, `--json` | 21-point health check |
| `rules` | Diagnostics | `--conflicts` | Show effective rules with inheritance markers |
| `config` | Diagnostics | `--chain` | Show effective config with inheritance chain |

---

## Configuration

| Setting | Default | Env var | TOML key |
|---------|---------|---------|----------|
| Project name | `default` | `MEMORY_PROJECT` | `[project] name` |
| Store path | `memory/store.jsonl` | — | `[store] path` |
| Neo4j URI | `bolt://localhost:7687` | `NEO4J_URI` | `[neo4j] uri` |
| Neo4j user | `neo4j` | `NEO4J_USER` | `[neo4j] user` |
| Neo4j password | (empty — set via env) | `NEO4J_PASSWORD` | — (env only) |
| Neo4j container name | `{project}-neo4j` | — | `[neo4j] container_name` |
| Neo4j HTTP port | 7474 | — | `[neo4j] http_port` |
| Neo4j Bolt port | 7687 | — | `[neo4j] bolt_port` |
| Voyage API key | (none) | `VOYAGE_API_KEY` | — (env only) |
| Embed model | `voyage-4-lite` | — | `[voyage] embed_model` |
| Embed dimensions | 1024 | — | `[voyage] embed_dimensions` |
| Rerank model | `rerank-2` | — | `[voyage] rerank_model` |
| Recency decay | 0.995 | — | `[retrieval] recency_decay` |
| Recall depth | 2 | — | `[retrieval] recall_depth` |
| Recall decay | 0.8 | — | `[retrieval] recall_decay` |
| Association k | 10 | — | `[retrieval] association_k` |
| L0 token budget | 2000 | — | `[retrieval] l0_token_budget` |
| Max inherit depth | 3 | — | `[retrieval] max_inherit_depth` |

---

## Testing

### Coverage

707 tests across 36 files + 2 Neo4j integration (deselected by default). 22/22 doctor checks.

| Category | Files | Tests |
|----------|------:|------:|
| Core store + config (store, neo4j_store, config, schema, init, migration) | 6 | 134 |
| Hierarchy + inheritance | 2 | 140 |
| Embedding + spaces (field_spaces, embeddings, reembed) | 3 | 74 |
| Gate + probes (write_gate, numeric_probe, l0_budget, validator) | 4 | 87 |
| Chain + lifecycle (chain_state, e2e_pipeline, consolidation, reflect, mitigates) | 5 | 49 |
| CLI commands | 11 | 84 |
| Eval + metrics | 1 | 24 |
| Other (tags, discovery, decline) | 3 | 35 |
| **Total (collected)** | **36** | **707** |
| Neo4j integration (deselected, `pytest -m integration`) | — | 2 |

### Mocking Patterns

| Dependency | Mock target | Pattern |
|-----------|-------------|---------|
| `voyageai.Client` | `memoryschema.embeddings.voyageai` | `patch("memoryschema.embeddings.voyageai")` — mock Client, embed, rerank returns |
| `neo4j.GraphDatabase` | `memoryschema.neo4j_store.GraphDatabase` | `patch("memoryschema.neo4j_store.GraphDatabase")` — mock driver, session, run |
| Docker CLI | `subprocess.run` | `patch("subprocess.run")` — mock container status, compose commands |
| Click CLI | `click.testing.CliRunner` | `runner.invoke(cli, ["command", "--flag"])` — test exit codes, output |
| File I/O | `tmp_path` fixture | pytest's built-in temp directory — real file ops, isolated |

### Diagnostics

`memoryschema doctor` — 21 live checks:

| Check | What | Fix on failure |
|-------|------|----------------|
| python | Python >= 3.11 | Upgrade |
| package | importable, version | Reinstall |
| config | MemoryConfig loads | Show missing env vars |
| memory_dir | memory/ exists | `memoryschema init` |
| memory_index | MEMORY.md exists | `memoryschema init` |
| rules | .claude/rules/memory-schema.md | `memoryschema init` |
| guidelines | scope guideline installed | `memoryschema init --scopes working` |
| toml_config | TOML syntax valid, project-name/directory match | Correct `memoryschema.toml` |
| rules_inherit | overridden rules count reported | `memoryschema rules --conflicts` |
| rules_hash | rules-file hash attestation | Re-run `memoryschema init` or restore rules |
| store_jsonl | store.jsonl accessible | `memoryschema init` |
| docker | Docker installed | Install Docker |
| neo4j_container | container running | `memoryschema neo4j deploy` |
| neo4j_connection | Bolt connection | `memoryschema neo4j up` |
| neo4j_schema | indexes present | `memoryschema neo4j schema` |
| neo4j_nodes | node count > 0 | `memoryschema index` |
| voyage_key | API key set | `export VOYAGE_API_KEY=...` |
| voyage_embed | test embed succeeds | Check key validity |
| hook | registered | `memoryschema hook install` |
| hook_script | exists, executable | Reinstall package |
| tests | pytest passes | Fix failing tests |

---

## Design Principles

1. **Schema + guidelines = core** — schema is structure (reusable), guidelines are usage (per-scope)
2. **Graceful degradation** — five layers, each independent
3. **Source of truth** — `docs/schema.md` is authoritative
4. **Importance-correlated enforcement** — 8-10 strict, 4-7 standard, 1-3 advisory
5. **Thin schema, rich guidelines** — 3 required fields, everything else optional
