<memory:entity schema="4" name="plugin-no-mcp" type="knowledge" importance="8" confidence="9">
  <memory:description>Plugin without MCP: hooks + rules + skills — packaging what we already have, not building new</memory:description>
  <memory:observations>
    <memory:observation>Plugin structure: manifest + hooks/hooks.json + rules/*.md + skills/*/SKILL.md</memory:observation>
    <memory:observation>Hooks: PostToolUse Write → embed/gate/store (exactly as current hook-post-write.sh)</memory:observation>
    <memory:observation>Rules: schema + working guidelines (exactly as current .claude/rules/*.md)</memory:observation>
    <memory:observation>Skills: recall, chain start/release, status — wrap CLI calls, discoverable by Claude without Bash syntax</memory:observation>
    <memory:observation>No MCP server — recall stays a CLI call under the hood, packaged as a skill for discoverability</memory:observation>
    <memory:observation>The current system IS this architecture — the work is packaging into plugin format, not building new</memory:observation>
  </memory:observations>
  <memory:prompt>We don't want to use an MCP server</memory:prompt>
  <memory:reasoning>Without MCP, the plugin is hooks (infrastructure), rules (context), and skills (procedures). This maps 1:1 to what exists: hook-post-write.sh becomes hooks/hooks.json, .claude/rules/ becomes rules/, and CLI commands become skills. The plugin packaging adds discoverability and portability — install via /plugin install instead of manual settings.json editing.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
