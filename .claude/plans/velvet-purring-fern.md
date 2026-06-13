# Fix Hook Embedding Gap

## Context

The PostToolUse hook constructs a `MemoryConfig` (line 82) but never passes it to `embed_text()` (line 73). The embed guard checks `os.environ.get('VOYAGE_API_KEY')` which isn't available in the hook subprocess. The config already supports reading the key from TOML or env. The CLI `hook test` command does it correctly: `embed_text(text, config=config)`.

## Prior Residuals (from [S4] bb5a825)

None.

## Phase 1 — Pass config to embed_text in hook

### 1.1 Fix hook embedding to use config
In `src/memoryschema/hooks/hook-post-write.sh`, two changes:

1. Move the embed block AFTER config construction (currently embed is lines 68-75, config is lines 78-89 — embed runs before config exists)
2. Change the embed guard to check config, and pass config to embed_text:

```python
# BEFORE (lines 68-75):
if os.environ.get('VOYAGE_API_KEY'):
    ...
    memory['embedding'] = embed_text(text)

# AFTER (moved after config construction):
if os.environ.get('VOYAGE_API_KEY') or (hook_config and hook_config.voyage_api_key):
    ...
    memory['embedding'] = embed_text(text, config=hook_config)
```

### 1.2 Add test
Add to `tests/test_cli_hook.py`:
- `test_embed_text_accepts_config` — verify `embed_text(text, config=config)` works with config that has voyage_api_key set (mocked Voyage client)

### Key file
- `src/memoryschema/hooks/hook-post-write.sh` — lines 68-89

**Verification:** Operative (write a test memory, verify it has an embedding)

## Verification Criteria

| # | Criterion | Phase | Status type |
|---|-----------|-------|-------------|
| 1 | Hook embeds on write using config (not just env) | 1 | Operative |
