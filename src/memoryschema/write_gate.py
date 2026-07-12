"""Pre-indexing write gate for memory mutations.

Three-verdict pipeline — every write gets an explicit verdict:

  REJECT     — structural failure (missing fields).
               Entry is never saved. Logged with reason.
  QUARANTINE — suspicious content (near-duplicate, numeric contradiction, L0 echo).
               Entry saved with status='quarantined', unembedded, pending review.
  ACCEPT     — passes all checks, indexed normally.

Pipeline stages:
  1. Validation    — schema structure (name required, description expected)
  2. Consistency   — embedding similarity check (strict mode only)
  3. Numeric probe — contradiction detection against active neighbours (v4)
  4. L0 echo       — restatement of MEMORY.md content without new material (v4)

Stages 5-6 require an embedding (for neighbour lookup in stage 5) and skip
with an audit note when embeddings are unavailable. Reasons from all stages
accumulate into a single verdict per the gate's existing shape.

Never silently drops — every entry gets a logged verdict.
Called by the PostToolUse hook and the CLI write command.
"""

from enum import Enum


class GateVerdict(str, Enum):
    ACCEPT = 'accept'
    REJECT = 'reject'
    QUARANTINE = 'quarantine'


class GateResult:
    """Result of a write gate pipeline evaluation."""

    __slots__ = ('verdict', 'reasons', 'warnings')

    def __init__(self, verdict, reasons=None, warnings=None):
        self.verdict = verdict
        self.reasons = reasons or []
        self.warnings = warnings or []

    @property
    def ok(self):
        return self.verdict == GateVerdict.ACCEPT

    def to_dict(self):
        return {
            'verdict': self.verdict.value,
            'reasons': self.reasons,
            'warnings': self.warnings,
        }


def gate_check(memory, store=None, strict=False):
    """Validate a memory dict before indexing.

    Backward-compatible wrapper around gate_pipeline().

    Returns:
        (ok, warnings) tuple:
            ok: True if the memory should be indexed (ACCEPT).
            warnings: List of warning/reason strings.
    """
    result = gate_pipeline(memory, store=store, strict=strict)
    return result.ok, result.reasons + result.warnings


def gate_pipeline(memory, store=None, strict=False, config=None):
    """Full write gate pipeline.

    Evaluates a parsed memory dict through six stages.
    Returns GateResult with verdict, reasons, and warnings.
    Never silently drops — every entry gets a verdict.

    Stage 2 (the near-duplicate consistency probe) runs only in strict mode. Production callers
    pass `strict=False`, so it is DORMANT by default; a deployment opts in via `gate.strict`
    (config) after measuring — the arg still wins when explicitly True.
    """
    warnings = []
    strict = strict or bool(getattr(config, 'gate_strict', False))

    # Stage 1: Validation
    name = memory.get('name')
    if not name:
        return GateResult(GateVerdict.REJECT, ['Missing name attribute'])

    description = memory.get('description')
    if not description:
        warnings.append('Missing description')

    # Quality nudges (warn-only; plan-memory-v5-sota-alignment step 2).
    # Chains are exempt from the description-length rule until v5 splits the
    # evolving summary into its own field — the v4 chain protocol REQUIRES a
    # growing description, so warning on it would just teach warning-blindness.
    is_chain = str(name).startswith('chain-')
    if description and not is_chain and len(description) > 120:
        warnings.append('description is %d chars (aim <=120 — one line; move detail '
                        'to observations/reasoning)' % len(description))
    imp = memory.get('importance')
    if imp is not None and store is not None:
        try:
            entries = store.list_all(include_inactive=False)
            if len(entries) >= 10:
                from collections import Counter
                dist = Counter(e.get('importance') for e in entries
                               if e.get('importance') is not None)
                mode, mode_n = dist.most_common(1)[0]
                if imp == mode and mode_n / max(sum(dist.values()), 1) > 0.4:
                    warnings.append('importance=%s is the store mode (%d%% of entries) '
                                    '— vary it or omit for default' %
                                    (imp, round(100 * mode_n / sum(dist.values()))))
        except Exception:
            pass  # nudge failure is never blocking

    # Stage 2: Consistency probe (strict mode)
    if strict and store is not None and memory.get('embedding'):
        try:
            probe_reason = _check_consistency(memory, store)
            if probe_reason:
                return GateResult(GateVerdict.QUARANTINE,
                                  [probe_reason], warnings)
        except Exception:
            pass  # Probe failure is non-blocking

    # Stage 5: Numeric contradiction probe (v4)
    # Stage 6: L0 echo probe (v4)
    # Both accumulate reasons; a single quarantine verdict is returned if any fire
    quarantine_reasons = []
    try:
        _run_v4_probes(memory, store, config, quarantine_reasons, warnings)
    except Exception:
        pass  # Probe failure is non-blocking

    if quarantine_reasons:
        return GateResult(GateVerdict.QUARANTINE, quarantine_reasons, warnings)

    return GateResult(GateVerdict.ACCEPT, warnings=warnings)


def _run_v4_probes(memory, store, config, quarantine_reasons, warnings):
    """Run v4 gate probes (stages 3-4). Non-blocking on failure."""

    # Get config values
    probe_enabled = getattr(config, 'numeric_probe_enabled', True) if config else True
    probe_mode = getattr(config, 'numeric_probe_mode', 'log') if config else 'log'
    echo_threshold = getattr(config, 'l0_echo_threshold', 0.6) if config else 0.6

    name = memory.get('name', '')

    # Stage 5: Numeric contradiction probe
    if probe_enabled and store is not None and memory.get('embedding'):
        try:
            from memoryschema.numeric_probe import extract_entity_claims, compare
            from memoryschema.store import _cosine_similarity

            sim_threshold = getattr(config, 'numeric_probe_sim_threshold', 0.80) if config else 0.80
            candidate_claims = extract_entity_claims(memory)

            if candidate_claims:
                # Fetch neighbours by cosine similarity
                entries = store.list_all(include_inactive=False)
                neighbours = []
                for entry in entries:
                    if entry.get('name') == name:
                        continue
                    if not entry.get('embedding'):
                        continue
                    sim = _cosine_similarity(memory['embedding'], entry['embedding'])
                    if sim >= sim_threshold:
                        neighbours.append(entry)

                if neighbours:
                    hits = compare(candidate_claims, neighbours)

                    # Apply escape valves per conflicting entity
                    candidate_rels = memory.get('relations', [])
                    candidate_targets = {
                        (r.get('target'), r.get('type')) for r in candidate_rels
                    }
                    filtered_hits = []
                    for hit in hits:
                        nname = hit['neighbour_name']
                        # Bypass: declared CONTRADICTS or SUPERSEDES toward this entity
                        if (nname, 'CONTRADICTS') in candidate_targets:
                            continue
                        if (nname, 'SUPERSEDES') in candidate_targets:
                            continue
                        filtered_hits.append(hit)

                    for hit in filtered_hits:
                        qual = f"/{hit['qualifier']}" if hit['qualifier'] else ''
                        reason = (
                            f"numeric-contradiction: {hit['unit']}{qual} "
                            f"{hit['candidate_value']} vs {hit['neighbour_value']} "
                            f"({hit['neighbour_name']})"
                        )
                        if probe_mode == 'quarantine':
                            quarantine_reasons.append(reason)
                        else:
                            # Log mode: audit record but don't affect verdict
                            warnings.append(f'[numeric-probe-hit] {reason}')
        except ImportError:
            warnings.append('numeric_probe unavailable — skipping stage 5')
    elif probe_enabled and store is not None and not memory.get('embedding'):
        warnings.append('no embedding — stage 5 (numeric probe) skipped')

    # Stage 6: L0 echo probe
    if store is not None:
        try:
            _check_l0_echo(memory, echo_threshold, quarantine_reasons, config)
        except Exception:
            pass

    # Source convention: memory:<name> denotes memory-citing-memory
    source = memory.get('source', '')
    if source and source.startswith('memory:'):
        warnings.append(f'source_is_memory: {source}')


def _check_l0_echo(memory, threshold, quarantine_reasons, config=None):
    """Check if the candidate restates an L0-resident entry without new content."""
    import os

    name = memory.get('name', '')
    # An already-inactive entity (superseded/archived/quarantined) is being RETIRED,
    # not competing for L0 — re-indexing it (e.g. the old holder during a keyed
    # supersession, which naturally echoes its successor) must not re-quarantine it.
    if (memory.get('status') or 'active') != 'active':
        return
    description = (memory.get('description') or '').lower()
    if not description:
        return

    # Resolve MEMORY.md from the config's project root FIRST — resolving relative
    # to the process CWD makes the stage silently no-op when the command is run
    # from another directory, and compares against the WRONG project's index when
    # cwd is a different vault. Fall back to cwd-relative only when no config.
    candidates = []
    if config is not None:
        idx = getattr(config, 'memory_index_path', None)
        root = getattr(config, 'project_root', None)
        if idx is not None:
            candidates.append(os.path.join(str(root), str(idx)) if root and not os.path.isabs(str(idx)) else str(idx))
    candidates += ['memory/MEMORY.md', 'MEMORY.md']
    for candidate_path in candidates:
        if os.path.exists(candidate_path):
            try:
                with open(candidate_path, encoding='utf-8') as f:
                    lines = f.readlines()
            except OSError:
                return
            break
    else:
        return

    # Parse L0 entries: "- [Name](file.md) -- description" or "- [Name](file.md) — description"
    l0_entries = {}
    for line in lines:
        line = line.strip()
        if not line.startswith('- ['):
            continue
        # Extract name and description
        bracket_end = line.find(']')
        if bracket_end < 0:
            continue
        entry_name = line[3:bracket_end]
        # Find description after -- or —
        for sep in [' -- ', ' — ', ' - ']:
            idx = line.find(sep)
            if idx >= 0:
                l0_entries[entry_name] = line[idx + len(sep):].strip().lower()
                break

    if not l0_entries:
        return

    # Stopwords for Jaccard
    _STOPWORDS = frozenset(
        'a an the is are was were be been being have has had do does did '
        'will would shall should may might can could of in to for with on '
        'at by from as into through during before after above below between '
        'out off over under again further then once here there when where '
        'why how all each every both few more most other some such no nor '
        'not only own same so than too very and but or if'.split()
    )

    def content_words(text):
        return {w for w in text.split() if w.isalnum() and w not in _STOPWORDS and len(w) > 1}

    candidate_words = content_words(description)
    if not candidate_words:
        return


    # Check for relations to targets outside echoed entry
    candidate_rel_targets = {r.get('target') for r in memory.get('relations', []) if r.get('target')}
    # Entries this candidate SUPERSEDES are exempt: a new version of a fact
    # legitimately restates-and-replaces the old one (the whole point of a keyed
    # supersession), so echoing the entry it supersedes must NOT quarantine it.
    superseded_targets = {r.get('target') for r in memory.get('relations', [])
                          if r.get('type') == 'SUPERSEDES' and r.get('target')}

    for entry_name, entry_desc in l0_entries.items():
        if entry_name == name or entry_name in superseded_targets:
            continue
        entry_words = content_words(entry_desc)
        if not entry_words:
            continue

        # Jaccard overlap
        intersection = candidate_words & entry_words
        union = candidate_words | entry_words
        overlap = len(intersection) / len(union) if union else 0

        if overlap >= threshold:
            # Check conjunction: no relation outside echoed entry
            external_targets = candidate_rel_targets - {entry_name}
            if not external_targets:
                quarantine_reasons.append(
                    f'l0-echo: restates {entry_name} without new content'
                )
                return  # One echo is enough


def _check_consistency(memory, store):
    """Check if a nearby entry has a contradictory description.

    Returns a reason string if quarantine is warranted, None otherwise.
    """
    from memoryschema.store import _cosine_similarity

    name = memory['name']
    embedding = memory['embedding']
    entries = store.list_all(include_inactive=True)

    for entry in entries:
        if entry.get('name') == name:
            continue
        if not entry.get('embedding'):
            continue

        sim = _cosine_similarity(embedding, entry['embedding'])
        if sim > 0.95:
            existing_desc = (entry.get('description') or '').lower()
            new_desc = (memory.get('description') or '').lower()
            if existing_desc and new_desc and existing_desc != new_desc:
                return (
                    f'Near-duplicate: "{name}" is 0.95+ similar to '
                    f'"{entry["name"]}" but has different description')
    return None
