"""Canonical embedding input composition.

Single source of truth for what text gets embedded for each space.
All callers (hook, CLI write, reembed, consolidation, examples) must
use this function — do not compose embedding text inline.

Architecture: 1:1 field-to-space mapping. Each entity field gets its
own embedding space. The default space blends all fields together.

TRUNCATION IS RECENCY-BIASED (plan-memory-v5-sota-alignment): the original
head-slice [:2000] made big chains embed only their OLDEST content — the
observations space represented step 1 from weeks ago and the default space
never got past the description (the measured retrieval defect behind the
session recall misses). Accumulating fields (observations, reasoning) now
truncate from the TAIL (newest first); the default space is composed as
name + description + the NEWEST observations that fit. Set-once/replaced
fields (name, description, prompt, chain) keep the head slice.
"""

import hashlib

DEFAULT_MAX_CHARS = 8000  # ~2k tokens — far under Voyage context; was 2000 (the defect)


def _tail_observations(obs_list, budget, anchor_first=True):
    """Select whole observations from the NEWEST backwards until the budget is
    spent, preserving chronological order. If room remains and anchor_first,
    prepend the first observation (the chain's origin) as an anchor."""
    if not obs_list:
        return []
    texts = [str(o) for o in obs_list]
    picked = []
    used = 0
    for t in reversed(texts):
        cost = len(t) + 1
        if used + cost > budget and picked:
            break
        picked.append(t)
        used += cost
        if used >= budget:
            break
    picked.reverse()
    # picked currently = newest K observations in chronological order
    if anchor_first and len(picked) < len(texts):
        first = texts[0]
        if first not in picked and used + len(first) + 1 <= budget:
            picked.insert(0, first)
    return picked


def compose_embedding_text(entry, space='default', max_chars=DEFAULT_MAX_CHARS):
    """Compose the text to embed for a memory entry.

    Args:
        entry: Memory dict with name, description, observations, etc.
        space: Which embedding space to compose for.
            'default' — name + description + newest observations (recency-biased)
            'name' — name only
            'description' — description only
            'observations' — newest observations first (whole-observation aligned)
            'reasoning' — the TAIL of the narrative (newest reasoning)
            'prompt' — prompt only
            'chain' — chain context only
        max_chars: Maximum character limit for the composed text.

    Returns:
        Composed text string ready for embedding.
    """
    if space == 'default':
        head_parts = [entry.get('name', ''), entry.get('description', ''),
                      entry.get('summary', '') or '']   # v5: the evolving summary
        head = ' '.join(p for p in head_parts if p).strip()
        head = head[:max_chars]
        budget = max_chars - len(head) - 1
        obs = entry.get('observations', [])
        if budget > 0 and obs:
            picked = _tail_observations(obs, budget)
            if picked:
                head = (head + ' ' + ' '.join(picked))[:max_chars]
        # prompt/reasoning/chain only if room remains. Reasoning contributes its
        # TAIL (newest narrative) — same recency bias as its own space.
        budget = max_chars - len(head) - 1
        if budget > 0:
            reasoning = entry.get('reasoning') or ''
            if len(reasoning) > budget:
                reasoning = reasoning[-budget:]
            extra = ' '.join(p for p in (entry.get('prompt'), reasoning,
                                         entry.get('chain')) if p)
            if extra:
                head = (head + ' ' + extra[:budget]).strip()
        return head[:max_chars]

    if space == 'name':
        name = entry.get('name', '')
        if not name:
            return ''
        return name[:max_chars]

    if space == 'description':
        desc = entry.get('description', '')
        summary = entry.get('summary') or ''            # v5: summary shares the description space
        text = (desc + ' ' + summary).strip() if summary else desc
        if not text:
            return ''
        return text[:max_chars]

    if space == 'observations':
        obs = entry.get('observations', [])
        if not obs:
            return ''
        picked = _tail_observations(obs, max_chars)
        text = ' '.join(picked).strip()
        return text[:max_chars] if len(text) > max_chars else text

    if space == 'prompt':
        prompt = entry.get('prompt', '') or ''
        if not prompt:
            return ''
        return prompt[:max_chars]

    if space == 'reasoning':
        reasoning = entry.get('reasoning', '') or ''
        if not reasoning:
            return ''
        # TAIL: chain reasoning is append-only (newest narrative after '---'
        # separators); the newest content is the retrieval-relevant content.
        return reasoning[-max_chars:] if len(reasoning) > max_chars else reasoning

    if space == 'chain':
        chain = entry.get('chain', '') or ''
        if not chain:
            return ''
        return chain[:max_chars]

    raise ValueError(f"Unknown embedding space: {space!r}")


def compose_full_text(entry):
    """The FULL untruncated concatenation of every embeddable field, in a fixed
    order. This is the provenance basis for embed_input_hash — any content
    change anywhere in the entity changes it, so stale embeddings are
    detectable even though the composed (truncated) inputs might not change."""
    parts = [
        entry.get('name', '') or '',
        entry.get('description', '') or '',
        entry.get('summary', '') or '',
        '\x1f'.join(str(o) for o in entry.get('observations', []) or []),
        entry.get('prompt', '') or '',
        entry.get('reasoning', '') or '',
        entry.get('chain', '') or '',
    ]
    return '\x1e'.join(parts)


def embed_input_hash(entry):
    """sha256[:16] of the full untruncated content — stored beside the
    embeddings at embed time; compared by reconcile/sync to detect
    content-vs-embedding drift (the 'Re-embedded: 0 on changed chains' bug:
    the old drift key was the truncated head text, which saturated fields
    never change)."""
    return hashlib.sha256(compose_full_text(entry).encode('utf-8')).hexdigest()[:16]
