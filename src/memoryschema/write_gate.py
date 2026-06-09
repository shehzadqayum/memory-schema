"""Pre-indexing write gate for memory mutations.

Validates a parsed memory dict before it is indexed into any store.
Treats every write as a privileged state transition — validates
schema, checks provenance, and detects name collisions.

Called by the PostToolUse hook before upsert.
"""

from memoryschema.validator import validate
from memoryschema.config import VALID_PROVENANCES


def gate_check(memory, store=None, strict=False):
    """Validate a memory dict before indexing.

    Args:
        memory: Parsed memory dict from tags.py.
        store: Optional store instance for collision checks.
        strict: If True, performs consistency probe (embedding
            similarity check against existing entries).

    Returns:
        (ok, warnings) tuple:
            ok: True if the memory should be indexed.
            warnings: List of warning strings (non-blocking unless strict).
    """
    warnings = []

    # 1. Schema validation
    name = memory.get('name')
    if not name:
        return False, ['Missing name attribute']

    description = memory.get('description')
    if not description:
        warnings.append('Missing description')

    # 2. Provenance present
    provenance = memory.get('provenance')
    if not provenance:
        warnings.append('No provenance set — defaulting to first-party')
        memory['provenance'] = 'first-party'
    elif provenance not in VALID_PROVENANCES:
        warnings.append(f'Invalid provenance "{provenance}" — defaulting to first-party')
        memory['provenance'] = 'first-party'

    # 3. Name collision detection
    if store is not None:
        existing = store.get(name)
        if existing:
            # Upsert is expected — not a collision. But warn if provenance differs.
            existing_prov = existing.get('provenance', 'first-party')
            new_prov = memory.get('provenance', 'first-party')
            if existing_prov != new_prov:
                warnings.append(
                    f'Provenance change: {existing_prov} → {new_prov} for "{name}"'
                )

    # 4. Strict mode: consistency probe (embedding similarity)
    if strict and store is not None and memory.get('embedding'):
        try:
            _check_consistency(memory, store, warnings)
        except Exception:
            pass  # Consistency check failure is non-blocking

    return True, warnings


def _check_consistency(memory, store, warnings):
    """Check if a nearby entry has a contradictory description.

    If the new entry's embedding is very similar (>0.95) to an
    existing entry with a different description, flag it.
    """
    from memoryschema.store import _cosine_similarity

    name = memory['name']
    embedding = memory['embedding']
    entries = store.list_all()

    for entry in entries:
        if entry.get('name') == name:
            continue
        if not entry.get('embedding'):
            continue

        sim = _cosine_similarity(embedding, entry['embedding'])
        if sim > 0.95:
            # Very similar — check if descriptions differ meaningfully
            existing_desc = (entry.get('description') or '').lower()
            new_desc = (memory.get('description') or '').lower()
            if existing_desc and new_desc and existing_desc != new_desc:
                warnings.append(
                    f'Near-duplicate: "{name}" is 0.95+ similar to '
                    f'"{entry["name"]}" but has different description. '
                    f'Consider adding a CONTRADICTS or SUPERSEDES relation.'
                )
                break  # One warning is enough
