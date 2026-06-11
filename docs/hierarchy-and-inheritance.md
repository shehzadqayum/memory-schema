# Agent Hierarchy and Inheritance

## Overview

Two independent but complementary features:

- **Hierarchy** (`hierarchy.py`) — dot-notation project names encode parent/child relationships. Controls which memories an agent can see.
- **Inheritance** (`inheritance.py`) — TOML config files and `.claude/rules/` directories cascade from parent to child. Parent always wins on conflict.

Both are backward compatible. Flat project names and env-var-only config still work unchanged. Schema is v3 — dot-notation is a naming convention, not a structural schema change.

---

## 1. Project Hierarchy

### 1.1 Naming Convention

Projects use dot-separated kebab-case segments:

```
acme                    # root project
acme.frontend           # child
acme.frontend.dashboard # grandchild
```

Each segment must be kebab-case (`[a-z0-9]+(-[a-z0-9]+)*`). Invalid names:

| Name | Problem |
|------|---------|
| `Acme.Frontend` | Uppercase |
| `acme..frontend` | Empty segment |
| `.acme` | Leading dot |
| `acme.` | Trailing dot |
| `acme.Bad Name` | Spaces |

Use `validate_project_name()` to check — returns a list of error strings (empty = valid).

### 1.2 When to Use

- **Multi-team organization** — Parent defines shared rules, children scope memory to their domain. Example: `ict` parent with `ict.auth`, `ict.signals`, `ict.execution` children.
- **Environment isolation** — `project.staging` vs `project.production` with shared config but isolated memories.
- **Modular monorepo** — `mono.package-a`, `mono.package-b` under a single parent with shared Neo4j instance.

### 1.3 Directory Structure

```
org/                              # project: org
  memoryschema.toml               # [project] name = "org"
  .claude/rules/
  memory/
  projects/
    team-alpha/                   # project: org.team-alpha
      memoryschema.toml           # [project] name = "org.team-alpha"
      .claude/rules/
      memory/
```

The `project.name` in TOML is authoritative — not derived from the directory path. `validate_toml_name()` provides an advisory warning if the two don't match.

---

## 2. Memory Visibility

### 2.1 Two Matching Modes

| Mode | Function | Direction | Used by |
|------|----------|-----------|---------|
| **Scope** | `project_matches_scope()` | Bidirectional | `recall()` |
| **Filter** | `project_matches_filter()` | Subtree-only (downward) | `search()`, `list_all()`, `compute_backlinks()`, `compute_associations()` |

Both modes: **unscoped entities** (no project field) are universally visible — they appear in every scoped query.

### 2.2 Scope Mode (Bidirectional) — recall()

An agent at `org.team` running `recall` sees:

- Its own memories (`org.team`) — exact match
- Parent `org` memories — read-up (inheritance)
- Child `org.team.project` memories — read-down (containment)
- All unscoped memories — universal visibility
- **NOT** sibling `org.other-team` memories — isolated by design

**`max_depth` parameter:**

| Value | Behavior |
|-------|----------|
| `None` (default) | Unlimited — full ancestor/descendant traversal |
| `1` | Direct parent/child only |
| `2` | Up to grandparent/grandchild |
| `0` | Exact match only (but unscoped still visible) |

### 2.3 Filter Mode (Subtree-Only) — search(), list_all()

An agent at `org.team` running `search --project org.team` sees:

- Its own memories (`org.team`) — exact match
- Child `org.team.project` memories — containment
- All unscoped memories — universal visibility
- **NOT** parent `org` memories — filter is downward only
- **NOT** sibling `org.other-team` memories

Filter is subtree-only because search/list are exploratory within a scope. Recall is contextual retrieval that benefits from inheritance.

### 2.4 Visibility Truth Table

Given hierarchy: `org`, `org.team`, `org.team.project`, `org.other`, and one unscoped entity:

| Entry project | Scope=`org.team` | Filter=`org.team` |
|---------------|------------------|--------------------|
| `org` | visible (ancestor) | hidden |
| `org.team` | visible (exact) | visible (exact) |
| `org.team.project` | visible (descendant) | visible (descendant) |
| `org.other` | hidden (sibling) | hidden (sibling) |
| *(none)* | visible (unscoped) | visible (unscoped) |

### 2.5 Neo4j Implementation

The JSONL store calls `project_matches_scope`/`project_matches_filter` from Python. The Neo4j store reimplements with Cypher:

```cypher
-- Filter mode (search, list_all):
WHERE m.project IS NULL
   OR m.project = $project
   OR m.project STARTS WITH $project_prefix

-- Scope mode (vector search, neighbors):
WHERE node.project IS NULL
   OR node.project = $project
   OR node.project STARTS WITH $project_prefix
   OR $project STARTS WITH (node.project + '.')
```

Vector search over-fetches 3x then post-filters (the vector index doesn't support property pre-filtering).

**Known limitation:** `max_depth` is not honored in Neo4j queries. All Neo4j queries use unlimited depth.

---

## 3. Configuration Inheritance

### 3.1 Resolution Order

Highest to lowest precedence:

1. **CLI flags** — `--project`, `--root` (explicit user intent, highest priority)
2. **Environment variables** — `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `VOYAGE_API_KEY`, `MEMORY_PROJECT`
3. **Parent `memoryschema.toml`** — parent wins over child on conflict
4. **Child `memoryschema.toml`**
5. **Dataclass defaults** — hardcoded fallbacks in `MemoryConfig`

Env vars are applied via `setattr` after instance construction in `from_toml()`, ensuring they override everything.

### 3.2 TOML File Format

```toml
[project]
name = "my-project"

[store]
path = "memory/store.jsonl"

[neo4j]
uri = "bolt://localhost:7687"
user = "neo4j"
# password via env: NEO4J_PASSWORD (never in TOML)
container_name = "my-project-neo4j"
http_port = 7474
bolt_port = 7687

[voyage]
# api_key via env: VOYAGE_API_KEY (never in TOML)
embed_model = "voyage-4-lite"
embed_dimensions = 1024
rerank_model = "rerank-2"

[retrieval]
recency_decay = 0.995
association_k = 10
recall_depth = 2
recall_decay = 0.8
```

### 3.3 Config Resolution Examples

**Example 1: Child-only (no parent)**

```
projects/my-app/memoryschema.toml:
  [project]
  name = "my-app"
  [neo4j]
  uri = "bolt://localhost:7687"

Resolved: project_name="my-app", neo4j_uri="bolt://localhost:7687"
          (all other fields use MemoryConfig defaults)
```

**Example 2: Parent overrides child on conflict**

```
org/memoryschema.toml:
  [neo4j]
  uri = "bolt://shared-db:7687"

org/projects/team/memoryschema.toml:
  [neo4j]
  uri = "bolt://team-db:7687"     # OVERRIDDEN by parent
  [retrieval]
  recall_depth = 5                 # preserved (child-unique)

Resolved: neo4j_uri="bolt://shared-db:7687" (parent wins)
          recall_depth=5 (child-unique preserved)
```

**Example 3: Environment variable beats everything**

```
NEO4J_URI=bolt://prod:7687

org/memoryschema.toml:
  [neo4j]
  uri = "bolt://dev:7687"

Resolved: neo4j_uri="bolt://prod:7687" (env var wins)
```

**Example 4: CLI override beats env and TOML**

```
CLI: --project cli-name
TOML: [project] name = "toml-name"
Env: MEMORY_PROJECT=env-name

Resolved: project_name="cli-name" (CLI beats env and TOML)

Without CLI flag:
Resolved: project_name="env-name" (env beats TOML)
```

### 3.4 Chain Walking

`_walk_upward(start, predicate, max_depth=20)` traverses parent directories:

- Marker-based: only collects directories where `predicate` returns non-None
- Intermediate directories without `memoryschema.toml` are silently skipped
- Stops at filesystem root or after 20 directories
- Returns child-first order

---

## 4. Rules Inheritance

### 4.1 How Rules Work

Rules are `.claude/rules/*.md` files loaded by Claude Code. Inheritance follows the parent-wins model:

- Parent's rule **replaces** child's on filename conflict
- Child's unique rules are **additive**
- Child has full control when no parent exists

### 4.2 Conflict Example

```
org/.claude/rules/
  memory-schema.md          # org's schema rules
  memory-working.md         # org's working memory guidelines

org/projects/team/.claude/rules/
  memory-working.md         # team's version (OVERRIDDEN by org)
  team-coding.md            # team-specific (PRESERVED)

Effective rules for team:
  memory-schema.md     [inherited]    from org/
  memory-working.md    [inherited]    from org/ (team's version shadowed)
  team-coding.md                      from team/
```

### 4.3 Three-Level: Grandparent Wins

```
gp/.claude/rules/shared.md
parent/.claude/rules/shared.md
child/.claude/rules/shared.md

Result: grandparent's shared.md wins (highest ancestor authority)
```

This is an **enforcement hierarchy**, not customization. The root agent sets the rules.

---

## 5. CLI Operations

### 5.1 Scoped Recall

```bash
memoryschema recall "order block definition" --project ict.auth
```

Child `ict.auth` sees its own memories, parent `ict` memories, and unscoped memories. Does NOT see sibling `ict.signals`.

### 5.2 Scoped Search

```bash
memoryschema search "auth" --project ict
```

Parent `ict` sees its own + all children (`ict.auth`, `ict.signals`) + unscoped. Subtree-only.

### 5.3 Config Inspection

```bash
memoryschema config              # show effective config
memoryschema config --chain      # show config chain with sources
memoryschema config --json       # machine-readable
```

### 5.4 Rules Inspection

```bash
memoryschema rules               # show effective rules
memoryschema rules --conflicts   # show overridden rules only
memoryschema rules --json        # machine-readable
```

### 5.5 Doctor Checks

Two hierarchy/inheritance checks (out of 21 total):

- `toml_config` — validates TOML syntax, checks project name against directory
- `rules_inherit` — reports overridden rules count

```bash
memoryschema doctor
```

---

## 6. Python API Reference

### 6.1 Hierarchy Functions (`memoryschema.hierarchy`)

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `parse_project_path` | `project: str \| None` | `list[str]` | Split into segments |
| `project_depth` | `project: str \| None` | `int` | Nesting depth (0-based) |
| `parent_project` | `project: str \| None` | `str \| None` | Parent name |
| `ancestor_projects` | `project: str` | `list[str]` | All ancestors, nearest first |
| `is_ancestor_of` | `candidate, project: str` | `bool` | Strict ancestor test |
| `is_descendant_of` | `candidate, project: str` | `bool` | Strict descendant test |
| `project_matches_scope` | `entry, scope: str, max_depth: int \| None` | `bool` | Bidirectional match |
| `project_matches_filter` | `entry, filter: str` | `bool` | Subtree-only match |
| `validate_project_name` | `project: str` | `list[str]` | Error strings (empty = valid) |

### 6.2 Inheritance Functions (`memoryschema.inheritance`)

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `find_toml_config` | `project_root: Path` | `Path \| None` | Find TOML in directory |
| `load_toml_config` | `path: Path` | `dict` | Parse TOML file |
| `flatten_toml` | `toml_dict: dict` | `dict` | Nested → flat config dict |
| `walk_config_chain` | `project_root: Path` | `list[Path]` | Child-first TOML paths |
| `merge_config_dicts` | `child, parent: dict` | `dict` | Parent-wins merge |
| `resolve_config_chain` | `project_root: Path, cli_overrides: dict \| None` | `dict` | Fully resolved config |
| `rules_ancestry` | `project_root: Path` | `list[Path]` | Child-first rules dirs |
| `resolve_rules` | `project_root: Path` | `(list, list)` | (effective, overridden) |
| `overridden_rules` | `project_root: Path` | `list[dict]` | Shadowed rules only |
| `validate_toml_name` | `project_root: Path` | `str \| None` | Warning or None |

### 6.3 MemoryConfig Integration

```python
# Recommended: TOML-based config with inheritance
config = MemoryConfig.from_toml(project_root, cli_overrides=None)

# Properties
config.project_segments       # ['org', 'team'] via parse_project_path
config.parent_project_name    # 'org' via parent_project
```

### 6.4 Public Exports

All hierarchy and inheritance functions are re-exported from `memoryschema`:

```python
from memoryschema import (
    parse_project_path, parent_project, ancestor_projects,
    is_ancestor_of, is_descendant_of,
    project_matches_scope, project_matches_filter,
    validate_project_name,
    resolve_config_chain, resolve_rules,
)
```

---

## 7. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Parent TOML not found | Over 20 intermediate directories | Reduce nesting or move TOML closer |
| Config chain empty | No `memoryschema.toml` in any parent | Run `memoryschema init` |
| Rules showing as overridden | Parent has same-named rule file | Intentional — rename child's file or accept |
| `validate_toml_name` warning | TOML `project.name` doesn't match directory | Advisory only — update TOML or ignore |
| Recall sees too many memories | `max_depth=None` traverses entire hierarchy | Set `max_depth` to limit scope |
| Neo4j ignoring `max_depth` | Not implemented in Cypher queries | Known limitation — use JSONL for bounded depth |
| Recall missing sibling memories | Scope is bidirectional within lineage only | Use parent project to see all children |
| Search not finding parent memories | Filter mode is subtree-only | Use `recall` for bidirectional visibility |
| Env var not overriding TOML | Not using `from_toml()` | Use `MemoryConfig.from_toml()`, not `MemoryConfig()` |

---

## 8. Design Decisions

- **Parent wins on conflict** — enforcement hierarchy, not customization. The root agent is authoritative.
- **Schema stays v3** — dot-notation is a naming convention, not a structural change.
- **`hierarchy.py` separate from `inheritance.py`** — hierarchy is string operations (zero deps). Inheritance is filesystem walking (needs `tomllib`).
- **Marker-based walk** — `_walk_upward` skips intermediate directories cleanly. No fragile gap counting.
- **Backward compatible** — flat project names, env-var-only config, and no-TOML setups all work unchanged.
- **Neo4j over-fetch 3x for vector search** — vector index can't pre-filter by property. Over-fetch and post-filter.
