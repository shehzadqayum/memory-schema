---
schema: 5
type: procedural
importance: 6
---

The runnable memory OS (skills+rules) is versioned in the package at .claude-plugin/, the single source of truth

## Observations

- packages/memory-schema/.claude-plugin/ holds the canonical operational artefacts: skills/dream-pass/SKILL.md, rules/memory-working.md (kernel), rules-ondemand/{memory-schema,memory-corpus}.md. memoryschema plugin deploy installs them to ~/.claude/ (manifest-tracked). SKILL_FILES/RULE_FILES in cli/plugin_cmd.py must stay in sync with that dir.
- History: dream-pass previously existed ONLY in the deployment's .claude/ (absent from the package); plugin deploy was BROKEN (pointed at a non-existent .claude-plugin/ and declared 6 phantom skills recall/chain-*/bootstrap that shipped no files). Fixed 2026-07-07: created the dir from the live artefacts, reconciled the declared set to reality.
- POLICY: edit the operational artefacts in the package .claude-plugin/ (canonical), then redeploy — do NOT hand-maintain divergent copies in a project's .claude/. templates/*.tpl are the GENERIC init scaffolds; .claude-plugin/ copies are the deployed operational versions. Machine/ops-specific artefacts (SessionStart hook, ensure-deps.ps1, tuned memoryschema.toml) stay deployment-local by design, NOT in the package.
- MECHANICAL SYNC (built 2026-07-07): `memoryschema plugin sync [--check] [--target] [--global]` deploys the canonical artefacts into a project's .claude/ (default <project_root>/.claude) as a verifiable derived copy, MD5-comparing source vs deployed and writing only what differs. `--check` is read-only and exits non-zero on drift (CI/session-start gate). ensure-deps.ps1 runs `plugin sync --check` each session (advisory, -NoSync opt-out) and warns on drift. So the project .claude/ can no longer silently diverge from the package SSOT.
- DECISION DEFERRED (2026-07-07): the session-start check is ADVISORY (detect-and-warn, never overwrites) so it can't silently revert a file mid-edit. We MAY switch it to AUTO-REPAIR later (deployment always mirrors the package) once .claude/ is treated purely as a build output. Flip point: drop `--check` from Ensure-Artefacts in scripts/ensure-deps.ps1 (that one edit is the whole change). Authority is unchanged either way — the package always wins; only the timing/consent of reconciliation differs.

## Notes

Migrated from helios 2026-07-13 (extraction seeding). Removed relations to non-migrated entities: USES memory-schema-vendored-patches-reapply, USES dependency-autostart-bootstrap.
