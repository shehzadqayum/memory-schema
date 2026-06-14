"""Canonical embedding input composition.

Single source of truth for what text gets embedded for each space.
All callers (hook, CLI write, reembed, consolidation, examples) must
use this function — do not compose embedding text inline.

The space parameter selects which fields to include. Future spaces
(observations-only, reasoning-only) will be added here as the
registry grows. The default space uses all five standard fields.
"""


def compose_embedding_text(entry, space='default', max_chars=2000):
    """Compose the text to embed for a memory entry.

    Args:
        entry: Memory dict with name, description, observations, etc.
        space: Which embedding space to compose for. Currently only
            'default' is supported (the blended whole-document space).
        max_chars: Maximum character limit for the composed text.

    Returns:
        Composed text string ready for embedding.
    """
    if space == 'default':
        parts = [
            entry.get('name', ''),
            entry.get('description', ''),
        ]
        parts.extend(str(o) for o in entry.get('observations', []))
        if entry.get('prompt'):
            parts.append(entry['prompt'])
        if entry.get('reasoning'):
            parts.append(entry['reasoning'])
        text = ' '.join(parts).strip()
        return text[:max_chars]

    if space == 'observations':
        obs = entry.get('observations', [])
        if not obs:
            return ''
        text = ' '.join(str(o) for o in obs).strip()
        return text[:max_chars]

    if space == 'reasoning':
        parts = []
        if entry.get('reasoning'):
            parts.append(entry['reasoning'])
        if entry.get('prompt'):
            parts.append(entry['prompt'])
        if not parts:
            return ''
        text = ' '.join(parts).strip()
        return text[:max_chars]

    if space == 'description':
        desc = entry.get('description', '')
        if not desc:
            return ''
        return desc[:max_chars]

    raise ValueError(f"Unknown embedding space: {space!r}")
