---
name: dream-pass
description: Memory consolidation session for a project's memory store — distill released chains into durable entities, merge duplicates, refresh stale keyed facts, archive dead weight. Run scheduled (weekly) or on demand when `memoryschema dream` shows candidates.
---

# The Dream Pass — memory consolidation

You are running the project's memory-consolidation session: the
industry-converged pattern (OpenAI Dreaming V3, Claude Code Auto Dream, Letta
sleep-time) implemented on our file-first substrate. **Code discovers, you judge,
the safe primitives act.** Nothing here bypasses the write gate, the audit trail,
or git — every action below is reversible and reviewable.

## Ground rules (non-negotiable)

- **Archive-never-destroy.** Never `delete`. Retire with `archive` or supersede.
- **Gated, selective evolution.** Act only on report candidates you can justify;
  when unsure, leave it — a false merge is worse than a missed one (D-MEM/SAGE).
- **No content invention.** Distillation quotes/compresses what the chain says;
  never add facts the source doesn't contain.
- **One commit at the end**, message prefixed `Memory(dream):`, listing actions.

## Procedure

1. **Setup + report**
   ```bash
   export PYTHONUTF8=1 PYTHONIOENCODING=utf-8   # activate your venv first if the package is in one
   memoryschema preflight && memoryschema sync
   memoryschema dream          # the candidate report (read-only)
   ```
   If sync shows drift, run `memoryschema reconcile` first. If the report says
   "nothing to dream about", record a one-line chain step and stop.

2. **Distill released chains** (highest value). For each released chain listed:
   - Read `memory/<chain>.md`. Identify the 1–4 DURABLE lessons — recurring
     hazards, validated patterns, decisions with lasting rationale — that are
     NOT already standalone memories (recall first to check).
   - For each: `memoryschema remember <kebab-name> --desc "…" --obs "…" [--obs …]
     --uses <chain-name> [--importance N]` — the `--uses` link preserves provenance.
   - Then `memoryschema archive <chain-name>` (its value now lives in the
     distillates; the chain stays recallable via `--include-inactive`).

3. **Merge duplicates.** For each pair at cosine ≥ 0.80: read both. If they are
   genuinely the same knowledge, write ONE merged entity
   (`remember merged-name … --supersedes a --supersedes b`); if distinct,
   leave them (optionally link with `--uses`). Record the decision either way.

4. **Refresh stale keyed facts.** For each: check whether the fact still holds
   (recall + read the source). Still true → re-remember with the SAME key
   (supersedes the old holder, resetting valid_from — an explicit re-validation).
   No longer true and no successor known → `archive` it. Unsure → leave, note it.

5. **Archive never-surfaced dead weight.** Only entities that are RESOLVED or
   EXPIRED (completed plans, fixed bugs). Reference facts stay even if unread.

6. **Attribution review** (`attribution_review` section; also `memoryschema
   attribution` for the full join). Entities recalled ≥3× but never cited
   (`chain step --uses` / `remember --uses|--informs` log citations at the
   moment they execute) are either RETRIEVAL NOISE — archive or sharpen the
   description so recall stops surfacing them — or AMBIENT VALUE (context
   carried them without an explicit cite): leave those and note the judgment.
   The rate only means something once the citation log has accumulated; early
   sessions should lean "leave, note it".

7. **Promote graduated knowledge** (`promotion_candidates` section: procedural
   entities, or anything cited ≥3×, not yet `promoted_to`). A memory that keeps
   being cited is behaving like a STANDING RULE — recall is the wrong delivery
   for it. Promote the distilled instruction into the surface where it belongs:
   - the kernel (`.claude/rules/memory-working.md`) for memory-protocol habits,
   - `CLAUDE.md` for project-wide operating rules,
   - a skill under `.claude/skills/` for multi-step procedures.
   Then mark it (the `promoted_to` frontmatter is a standing-surface pointer):
   `python -c "from memoryschema.write_index import set_lifecycle; set_lifecycle('memory/<name>.md', promoted_to='<surface>')"`
   + re-index — it drops off the candidate list but stays recallable with full
   provenance. Promote at most 1–2 per pass; a bloated kernel is a regression (the L0
   token budget is what's being protected).

8. **Verify + close**
   ```bash
   memoryschema reconcile     # heals + re-embeds anything the pass touched
   memoryschema dream         # should show fewer candidates
   memoryschema recall "<spot-check a distilled lesson>" --limit 3
   ```
   Record a chain step summarizing actions taken/skipped and why, then
   `git add -A && git commit` (the `Memory(dream): …` message).

## Cadence

Weekly, or when `memoryschema dream` shows ≥3 candidates, or immediately after
releasing a large chain. Keep sessions small: a pass that acts on 3–5 candidates
well beats one that churns everything.
