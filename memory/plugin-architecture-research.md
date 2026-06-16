<memory:entity schema="4" name="plugin-architecture-research" type="knowledge" importance="9" confidence="8">
  <memory:description>Claude Code plugin system: manifest + MCP server + hooks + skills + rules — memory system can be packaged as a formal plugin</memory:description>
  <memory:observations>
    <memory:observation>Claude Code has a formal plugin system: .claude-plugin/plugin.json manifest, marketplace distribution, scoped installation</memory:observation>
    <memory:observation>Extension mechanisms: hooks (automatic lifecycle events), MCP servers (tools), skills (model-invoked procedures), slash commands (user-invoked), rules (context instructions)</memory:observation>
    <memory:observation>The biggest upgrade: CLI → MCP server. Recall/write/search become native tools Claude calls directly, no Bash wrapping</memory:observation>
    <memory:observation>Current system maps: hook-post-write.sh → hooks/hooks.json, .claude/rules/ → plugin rules/, memoryschema CLI → MCP server</memory:observation>
    <memory:observation>PreToolUse hook or model-invoked skill could replace the behavioral "recall before responding" rule with code enforcement</memory:observation>
    <memory:observation>Plugin marketplace supports official, community, and private/team registries</memory:observation>
    <memory:observation>All backend logic exists — main work is MCP server wrapper and plugin manifest</memory:observation>
  </memory:observations>
  <memory:prompt>Can the current memory module be installed as a plugin for claude-code using plugin guidelines?</memory:prompt>
  <memory:reasoning>The memory system's current integration (hooks in settings.json, rules in .claude/rules/, CLI via Bash) is ad-hoc. The plugin system provides a formal packaging mechanism that bundles hooks, rules, MCP tools, and skills into one installable unit. The key upgrade is MCP: turning memoryschema recall/write/search into native tools removes the Bash wrapper and makes memory a first-class capability rather than a CLI workaround.</memory:reasoning>
  <memory:chain>evolving the memory system's data model toward immutability</memory:chain>
</memory:entity>
