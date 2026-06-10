"""Pre-indexing write gate for memory mutations.

Two-verdict pipeline — every write gets an explicit verdict:

  REJECT     — structural failure (missing fields, invalid provenance).
               Entry is never saved. Logged with reason.
  QUARANTINE — suspicious content (provenance mismatch, near-duplicate).
               Entry saved with status='quarantined', unembedded, pending review.
  ACCEPT     — passes all checks, indexed normally.

Pipeline stages:
  1. Validation    — schema structure (name required, description expected)
  2. Provenance    — valid provenance, source required for ingested (V13)
  3. Guards        — provenance mismatch detection on upsert
  4. Consistency   — embedding similarity check (strict mode only)

Never silently drops — every entry gets a logged verdict.
Called by the PostToolUse hook and the CLI write command.
"""

from enum import Enum

from memoryschema.config import VALID_PROVENANCES


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


def gate_pipeline(memory, store=None, strict=False):
    """Full write gate pipeline.

    Evaluates a parsed memory dict through four stages.
    Returns GateResult with verdict, reasons, and warnings.
    Never silently drops — every entry gets a verdict.
    """
    warnings = []

    # Stage 1: Validation
    name = memory.get('name')
    if not name:
        return GateResult(GateVerdict.REJECT, ['Missing name attribute'])

    description = memory.get('description')
    if not description:
        warnings.append('Missing description')

    # Stage 2: Provenance admission
    provenance = memory.get('provenance')
    if not provenance:
        warnings.append('No provenance set — defaulting to first-party')
        memory['provenance'] = 'first-party'
    elif provenance not in VALID_PROVENANCES:
        warnings.append(f'Invalid provenance "{provenance}" — defaulting to first-party')
        memory['provenance'] = 'first-party'

    if memory.get('provenance') == 'ingested' and not memory.get('source'):
        return GateResult(GateVerdict.REJECT,
                          [f'Ingested entry "{name}" requires source field'])

    # Stage 3: Guards
    if store is not None:
        existing = store.get(name)
        if existing:
            existing_prov = existing.get('provenance', 'first-party')
            new_prov = memory.get('provenance', 'first-party')
            if existing_prov != new_prov:
                return GateResult(
                    GateVerdict.QUARANTINE,
                    [f'Provenance mismatch on upsert: existing={existing_prov}, '
                     f'new={new_prov} for "{name}"'],
                    warnings)

    # Stage 4: Consistency probe (strict mode)
    if strict and store is not None and memory.get('embedding'):
        try:
            probe_reason = _check_consistency(memory, store)
            if probe_reason:
                return GateResult(GateVerdict.QUARANTINE,
                                  [probe_reason], warnings)
        except Exception:
            pass  # Probe failure is non-blocking

    return GateResult(GateVerdict.ACCEPT, warnings=warnings)


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
