# Centralize env var reads (Session 1 Residual)

## Context

From `[S4] 5fc565b` residual ledger: `os.environ` reads in `neo4j_store.py` and `embeddings.py` are direct, not routed through `config.py`. This creates dual read paths that can diverge.

Currently 5 direct `os.environ` reads outside `config.py`:
- `neo4j_store.py:22-24` — `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` as module-level defaults
- `embeddings.py:37,41` — `VOYAGE_API_KEY` in `get_client()`

`config.py` already reads the same 4 env vars via `field(default_factory)`. The module-level reads are fallbacks for when no `config` is passed to constructors.

## Prior Residuals (from [S4] 5fc565b)

- R1: os.environ reads in neo4j_store.py and embeddings.py → addressing (this plan)

## Fix

### `neo4j_store.py`
Remove module-level `_DEFAULT_*` constants. In `Neo4jMemoryStore.__init__()`, when no `config` and no explicit params, import and use `MemoryConfig` defaults directly:

```python
def __init__(self, uri=None, user=None, password=None, config=None):
    if config is None and uri is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()
    if config:
        uri = uri or config.neo4j_uri
        user = user or config.neo4j_user
        password = password or config.neo4j_password
    self._driver = GraphDatabase.driver(uri, auth=(user, password))
```

Remove `import os` (no longer needed).

### `embeddings.py`
In `get_client()`, when no `api_key` and no `config`, import and use `MemoryConfig` defaults:

```python
if api_key is None and config is None:
    from memoryschema.config import MemoryConfig
    config = MemoryConfig()
if api_key is None and config:
    api_key = config.voyage_api_key
```

Remove `os.environ.get('VOYAGE_API_KEY')` calls. Remove `import os`.

## Files to Modify

| File | Change |
|------|--------|
| `src/memoryschema/neo4j_store.py` | Remove `_DEFAULT_*` constants, use `MemoryConfig()` fallback |
| `src/memoryschema/embeddings.py` | Remove `os.environ` reads, use `MemoryConfig()` fallback |
| `tests/test_neo4j_store.py` | Update mocks (no more module-level env reads) |
| `tests/test_embeddings.py` | Update mocks |

## Verification

1. `python -m pytest tests/ -v` — all tests pass
2. `grep -r "os\.environ" src/memoryschema/ --include="*.py"` — only `config.py`
3. `memoryschema doctor` — 20/20
