# Phase 7 — Session Report Sequencing Amendments

**Status:** Patch specification for operator review and application.
**Reason:** The session-workflow skills (checkpoint, session-close) are shared infrastructure in `~/.claude/skills/`, used by every project on this machine. Direct editing carries regression risk for unrelated projects. This patch specification documents the exact changes for the operator to apply.

## Defect (D7)

Session reports are generated at checkpoint; the session-close step then creates one further commit (the "unit" commit). Every comparable session shows the report's commit count exactly one short of the close record, and the report's "Latest commit" is never the true final commit.

## Amendment 1: Checkpoint Skill

**File:** `~/.claude/skills/checkpoint` (or project-local `.claude/skills/checkpoint`)

**Location:** The section that generates the session report's "Current State" block.

**Change:** The Current State section must carry the marker:

```
- **Latest commit:** `<hash>` (as of checkpoint; close commit pending)
```

Instead of:

```
- **Latest commit:** `<hash>`
```

**Rationale:** The report cannot contain the hash of the commit that contains it. This marker makes the limitation explicit rather than silently approximate.

## Amendment 2: Session-Close Skill

**File:** `~/.claude/skills/session-close` (or project-local `.claude/skills/session-close`)

**Location:** After creating the close ("unit") commit, before the final report to the user.

**Change:** After the close commit is created, amend the session report file:

1. Update the commit count to be inclusive of the close commit (N+1).
2. Update the Current State to read:

```
- **Latest working commit:** `<hash>`; close commit: see execution log.
```

3. Stage and include the amended report in the close commit, OR create a follow-up commit.

**Rationale:** The report cannot contain the hash of the commit that contains it; the convention above resolves this honestly: counts become exact, the one unknowable hash is delegated to the mechanical log.

## Amendment 3: Backfill

Apply to the most recent session report only (if desired). Do not rewrite historical reports wholesale.

**Erratum convention for older reports:** If an older report is ever corrected, append a single line:

```
*Erratum (YYYY-MM-DD): <what was corrected and why>*
```

## Amendment 4: Memory Entity Basis Labels

If session reports are also written as memory entities (e.g., session-close memory files):

- At checkpoint time: commit-count observations should carry `basis="reported"` (the count is accurate at that moment but will change).
- After the close-time amendment: append a new `basis="measured"` observation with the final count. Do NOT relabel the existing observation (basis is immutable per schema v4).

**Example:**

```xml
<memory:observation basis="reported">5 commits in session</memory:observation>
<!-- After close: -->
<memory:observation basis="measured">6 commits in session (including close)</memory:observation>
```

## Verification

After applying these amendments:
- VC 10: The checkpoint report carries the "as of checkpoint; close commit pending" marker.
- VC 10: The close-amended count matches the execution log's commit count.

If the skills directory is not writable or the operator prefers not to apply, mark VC 10 as "delivered as specification" — this document satisfies the plan requirement.
