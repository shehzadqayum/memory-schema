"""Canonical embedding input composition.

Single source of truth for what text gets embedded for each space.
All callers (hook, CLI write, reembed, consolidation, examples) must
use this function — do not compose embedding text inline.

Architecture: 1:1 field-to-space mapping. Each entity field gets its
own embedding space. The default space blends all fields together.
"""


def compose_embedding_text(entry, space='default', max_chars=2000):
    """Compose the text to embed for a memory entry.

    Args:
        entry: Memory dict with name, description, observations, etc.
        space: Which embedding space to compose for.
            'default' — all fields blended
            'name' — name only
            'description' — description only
            'observations' — observations only
            'reasoning' — reasoning only
            'prompt' — prompt only
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

    if space == 'name':
        name = entry.get('name', '')
        if not name:
            return ''
        return name[:max_chars]

    if space == 'description':
        desc = entry.get('description', '')
        if not desc:
            return ''
        return desc[:max_chars]

    if space == 'observations':
        obs = entry.get('observations', [])
        if not obs:
            return ''
        text = ' '.join(str(o) for o in obs).strip()
        return text[:max_chars]

    if space == 'prompt':
        prompt = entry.get('prompt', '') or ''
        if not prompt:
            return ''
        return prompt[:max_chars]

    if space == 'reasoning':
        reasoning = entry.get('reasoning', '') or ''
        if not reasoning:
            return ''
        return reasoning[:max_chars]

    raise ValueError(f"Unknown embedding space: {space!r}")
