---
schema: 5
importance: 6
relations:
  - USES memory-artefacts-package-source
---

2026-07-11 evaluation: extracting packages/memory-schema to its own repo is feasible+clean but deferred until a 2nd consumer exists

## Observations

- FEASIBLE AND CLEAN: package is standalone (no imports from helios; src has zero helios paths; bare-install verified with optional deps blocked; 881 tests pass env-free via the hermetic conftest). History split is safe: 35/345 helios commits touch the path, git-verified free of the .env secret VALUES, acct 2295262, and balances across ALL 35 commits; tracked payload is 1.18 MB / 181 files (the ~20 MB tree is pycache/coverage junk + 64KB-cluster inflation). git subtree split works (filter-repo not installed; package present since the initial commit, no renames).
- RECOMMENDATION: defer hard extraction until a second real consumer exists (Aurora has ZERO memoryschema usage; recorded direction is service-boundary integration per [[aurora-helios-coupling]]). Zero option cost: a subtree split is available any time retroactively, and external consumption is ALREADY possible today via pip install git+https://github.com/shehzadqayum/helios.git#subdirectory=packages/memory-schema. If extracting, model ranking: (1) git subtree (tree path byte-identical -> hooks/.pth/plugin-sync/docs ALL unchanged; adds a split/push publish channel), (2) submodule (path-identical but two-repo commit dance), (3) sibling editable (reintroduces the relocation-tie half of the 2026-06-24 deprecation), (4) pinned git dep = BLOCKED: .claude-plugin is NOT package-data so plugin sync/deploy exit 1 on any non-source install (plugin_cmd._find_plugin_dir walks the SOURCE tree only), no git tags exist to pin, and it severs the same-session host+package dev loop (21 of 35 commits are mixed).
- EXTRACTION-DAY BREAKAGE (if ever done): (1) ~/.claude/settings.json:9,20 hook paths dangle SILENTLY (bash exit 127, non-blocking; preflight does NOT check hooks; ensure-deps never runs hook status) -> repoint via memoryschema hook uninstall+install then FIX WINDOWS BACKSLASHES + verify hook status + a live hand-edit; (2) the .venv editable .pth dangles if the tree is deleted before reinstall -> failure MISREPORTS as a Neo4j outage in ensure-deps; reinstall BEFORE removing; (3) .claude-plugin path refs inside the SSOT artefacts (memory-working.md:46 cd packages/memory-schema; rules-ondemand spec paths) must be fixed in the NEW repo then plugin-synced down, else the session-start MD5 gate warns forever; (4) requirements.txt:3-6, CLAUDE.md hook paragraph, HANDOVER.md sections 1+5 all reference the vendored layout; (5) fresh-machine bootstrap becomes two private clones.
- KEY DISCOVERIES: an OLD upstream repo github.com/shehzadqayum/memory-schema EXISTS with fully disjoint pre-vendor history (HEAD 13fbb7c not in helios objects) and LACKS every local patch -- any extraction must supersede/archive it or merge with --allow-unrelated-histories, and must seed FROM packages/memory-schema (the patched lineage), never from the stale sibling C:/Users/Caldera/Projects/memory-schema (no .git, frozen 2026-06-22). The vendored tree is the de-facto upstream; extraction would dissolve the re-apply-on-re-vendor doctrine ([[memory-schema-vendored-patches-reapply]] becomes obsolete). Keep any split repo PRIVATE: docs/reports/2026-06-21-trading-journal-setup-report.md leaks environment metadata (terminal paths, GitHub username, entity names) though no secrets/balances. CLAUDE.md's hook-upgrade-overwrites-patches warning is STALE: hook upgrade only rewrites settings.json entries, never the scripts.

## Notes

Migrated from helios 2026-07-13 (extraction seeding).
