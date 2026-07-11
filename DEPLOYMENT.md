# Deployment architecture — one source of truth, many projects

How this module is shared across projects: a **single-source-of-truth repo**, **git-subtree vendoring**,
per-project **`deployments/<project>` branches**, and a **machine-stamped ledger**. The goal is that "which
projects use memory-schema, at what version, vendored where" is always answerable from git itself — never a
hand-maintained list that rots (the same lesson that retired `HANDOVER.md`).

## The model

```
                    memory-schema repo  (SINGLE SOURCE OF TRUTH)
                    ├── main ................. the canonical module
                    ├── deployments/helios ... helios's vendored state (subtree-pushed)
                    ├── deployments/foo ...... foo's vendored state
                    └── deployments/*.toml ... the ledger (one per project, on main)
                              ▲   │
                    subtree push│   │subtree pull (updates)
                              │   ▼
   consumer repo (helios)  ───┴───────►  packages/memory-schema/   (vendored copy = canonical for that repo)
```

- **`main`** is the module. Improvements land here (via review), and every consumer pulls from here.
- **Consumers vendor via `git subtree`** — the vendored copy becomes self-contained inside the consumer repo
  (no submodule detached-HEAD/Windows friction; the consumer stays independently buildable, which is also its
  redundancy). This is the in-situ co-development pattern this module was built with.
- **`deployments/<project>`** is a branch on the module repo holding that project's pushed subtree state — so
  a project's local edits are visible on the module side and can be reviewed back into `main`.
- **The ledger** (`deployments/<project>.toml` on `main`) records the pointer + last-sync facts, written by
  `memoryschema deploy register` — deterministic tooling, never hand-edited.

**Rejected alternatives:** a PyPI-registry model (kills the in-situ co-development while the module is still
co-evolving with its first consumers); git submodules (pointer friction + breaks the consumer repo's
self-containment).

## Workflow

**Extract the module to its own repo** (one-time, from a consumer that vendors it):
```bash
git subtree split --prefix=packages/memory-schema -b memory-schema-main
# push memory-schema-main to a new private repo's `main`
```

**Adopt it in a new consumer** (see also `BOOTSTRAP.md`):
```bash
git subtree add --prefix packages/memory-schema <module-repo> main --squash
```

**Push a consumer's state to its deployment branch** (from the consumer repo):
```bash
git subtree push --prefix packages/memory-schema <module-repo> deployments/<project>
```

**Pull module updates into a consumer:**
```bash
git subtree pull --prefix packages/memory-schema <module-repo> main --squash
```

**Record / inspect the ledger** (from the module repo):
```bash
memoryschema deploy register --project <name> --repo-url <consumer-url> --prefix packages/memory-schema
memoryschema deploy status          # reconciles the ledger against the deployments/* branches
```

## The ledger

`deploy register` writes `deployments/<project>.toml` (machine-stamped — do not hand-edit):
```toml
[deployment]
project = "helios"
repo_url = "https://github.com/me/helios.git"
subtree_prefix = "packages/memory-schema"
scopes = ["working"]
schema_version = 5           # stamped from CURRENT_ENTITY_FORMAT
branch = "deployments/helios"
module_commit = "<module HEAD at register time>"
consumer_commit = ""         # optionally: the consumer HEAD at last sync
registered_at = "2026-07-11"
note = ""
```

`deploy status` reconciles the ledger files against the actual `deployments/*` branches and flags any
disagreement — a ledger entry with **no branch** = *registered-but-not-pushed*; a branch with **no ledger
entry** = *unregistered*. Because both the entries and the branches are derived from git, the ledger can never
silently drift from reality — the whole point of making it machine-stamped rather than a prose list.
