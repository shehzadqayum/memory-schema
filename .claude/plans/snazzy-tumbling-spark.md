# Sync Templates from Global Rules

## Context

The template files in `src/memoryschema/templates/` are stale snapshots from an older schema version. The deployed global rules at `~/.claude/rules/` (and the plugin copies at `.claude-plugin/rules/`) are the current authoritative versions — they include chain lifecycle, Edit-not-Write guidance, reasoning accumulation, Write|Edit enforcement, and Stop hook documentation. The templates have none of this. Since the `.tpl` files are plain markdown with no Jinja/templating logic, they can be replaced entirely.

## Prior Residuals (from [S4] 5736cb3)

- None — ledger is empty

---

## Phase 1 — Replace templates with current global rules content

### 1.1 `src/memoryschema/templates/memory-working.tpl`

Replace entire file with content from `~/.claude/rules/memory-working.md` (which matches `.claude-plugin/rules/memory-working.md`).

### 1.2 `src/memoryschema/templates/memory-schema.rules.tpl`

Replace entire file with content from `~/.claude/rules/memory-schema.md` (which matches `.claude-plugin/rules/memory-schema.md`).

### Verify

```bash
diff src/memoryschema/templates/memory-working.tpl .claude-plugin/rules/memory-working.md  # Should match
diff src/memoryschema/templates/memory-schema.rules.tpl .claude-plugin/rules/memory-schema.md  # Should match
pytest tests/ -x -q  # All tests pass
```

---

## Phase 2 — Documentation alignment audit

Verify all docs reflect that templates are now current. Same pattern as sessions 29/30.

### 2.1 `CHANGELOG.md`

- Changed entry: templates synced from global rules (memory-working.tpl, memory-schema.rules.tpl)

### 2.2 `docs/technical-reference.md`

- If templates are mentioned, verify they reference the current content (chain lifecycle, Edit-not-Write, etc.)

### 2.3 `README.md`

- Verify `memoryschema init` description reflects that templates now include full chain lifecycle + hook guidance

### Verify

```bash
grep -n "template\|\.tpl" docs/technical-reference.md README.md  # Check references
pytest tests/ -x -q  # Still green
```

---

## File Inventory

| File | Change | Phase |
|------|--------|-------|
| `src/memoryschema/templates/memory-working.tpl` | Replace with current global rules content | 1.1 |
| `src/memoryschema/templates/memory-schema.rules.tpl` | Replace with current global rules content | 1.2 |
| `CHANGELOG.md` | Changed entry for template sync | 2.1 |
| `docs/technical-reference.md` | Verify/update template references | 2.2 |
| `README.md` | Verify/update init description | 2.3 |
