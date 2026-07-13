---
schema: 5
importance: 9
---

Claude Code plugin system: manifest + MCP server + hooks + skills + rules — memory system can be packaged as a formal plugin

## Observations

- Claude Code has a formal plugin system: .claude-plugin/plugin.json manifest, marketplace distribution, scoped installation
- Extension mechanisms: hooks (automatic lifecycle events), MCP servers (tools), skills (model-invoked procedures), slash commands (user-invoked), rules (context instructions)
- The biggest upgrade: CLI → MCP server. Recall/write/search become native tools Claude calls directly, no Bash wrapping
- Current system maps: hook-post-write.sh → hooks/hooks.json, .claude/rules/ → plugin rules/, memoryschema CLI → MCP server
- PreToolUse hook or model-invoked skill could replace the behavioral "recall before responding" rule with code enforcement
- Plugin marketplace supports official, community, and private/team registries
- All backend logic exists — main work is MCP server wrapper and plugin manifest

## Reasoning

The memory system's current integration (hooks in settings.json, rules in .claude/rules/, CLI via Bash) is ad-hoc. The plugin system provides a formal packaging mechanism that bundles hooks, rules, MCP tools, and skills into one installable unit. The key upgrade is MCP: turning memoryschema recall/write/search into native tools removes the Bash wrapper and makes memory a first-class capability rather than a CLI workaround.

## Prompt

Can the current memory module be installed as a plugin for claude-code using plugin guidelines?

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
