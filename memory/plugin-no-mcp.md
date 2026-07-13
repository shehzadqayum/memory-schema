---
schema: 5
importance: 8
---

Plugin without MCP: hooks + rules + skills — packaging what we already have, not building new

## Observations

- Plugin structure: manifest + hooks/hooks.json + rules/*.md + skills/*/SKILL.md
- Hooks: PostToolUse Write → embed/gate/store (exactly as current hook-post-write.sh)
- Rules: schema + working guidelines (exactly as current .claude/rules/*.md)
- Skills: recall, chain start/release, status — wrap CLI calls, discoverable by Claude without Bash syntax
- No MCP server — recall stays a CLI call under the hood, packaged as a skill for discoverability
- The current system IS this architecture — the work is packaging into plugin format, not building new

## Reasoning

Without MCP, the plugin is hooks (infrastructure), rules (context), and skills (procedures). This maps 1:1 to what exists: hook-post-write.sh becomes hooks/hooks.json, .claude/rules/ becomes rules/, and CLI commands become skills. The plugin packaging adds discoverability and portability — install via /plugin install instead of manual settings.json editing.

## Prompt

We don't want to use an MCP server

## Chain

evolving the memory system's data model toward immutability

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
