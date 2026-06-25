"""Embedding space registry and variance-weighted combiner.

The registry is a declared catalogue of embedding spaces — one per
entity field plus a default blend. The combiner uses per-entry
divergence profiles to weight spaces automatically: distinctive fields
get amplified, redundant fields get suppressed. No base weights, no
query classification, no heuristics.

Architecture:
- 1:1 field-to-space mapping: name, description, observations, prompt, reasoning
- Default space: all fields blended
- Combiner: variance-weighted — divergence from default IS the weight
"""

from memoryschema.embedding_input import compose_embedding_text


# --- Space Registry ---

class SpaceDefinition:
    """Definition of a single embedding space."""

    __slots__ = ('name', 'space_type', 'input_selector', 'embedder')

    def __init__(self, name, space_type='immutable', input_selector=None, embedder='voyage'):
        self.name = name
        self.space_type = space_type  # 'immutable' or 'mutable' (future)
        self.input_selector = input_selector or name
        self.embedder = embedder

    def compose_input(self, entry):
        """Compose embedding input text for this space."""
        return compose_embedding_text(entry, space=self.input_selector)


# Registry: 1:1 field-to-space mapping + default blend
_REGISTRY = {
    'default': SpaceDefinition('default', 'immutable', 'default', 'voyage'),
    'name': SpaceDefinition('name', 'immutable', 'name', 'voyage'),
    'description': SpaceDefinition('description', 'immutable', 'description', 'voyage'),
    'observations': SpaceDefinition('observations', 'immutable', 'observations', 'voyage'),
    'prompt': SpaceDefinition('prompt', 'immutable', 'prompt', 'voyage'),
    'reasoning': SpaceDefinition('reasoning', 'immutable', 'reasoning', 'voyage'),
    'chain': SpaceDefinition('chain', 'immutable', 'chain', 'voyage'),
}


def get_registry():
    """Return the current space registry."""
    return dict(_REGISTRY)


def get_space(name):
    """Look up a space definition by name."""
    return _REGISTRY.get(name)


# --- Combiner ---

def combine_similarities(per_space_sims, divergence_profile=None):
    """Combine per-space similarities into a single score.

    Variance-weighted: uses per-entry divergence profile to weight spaces.
    Distinctive fields (high divergence from default) get amplified when
    the query matches them. Redundant fields (low divergence) get suppressed.

    Args:
        per_space_sims: dict mapping space_name → cosine similarity score.
        divergence_profile: dict mapping space_name → divergence from default
            (precomputed at embed time). If None, falls back to equal weighting.

    Returns:
        Combined similarity score (float).
    """
    if not per_space_sims:
        return 0.0

    # Single space: return directly
    if len(per_space_sims) == 1:
        return next(iter(per_space_sims.values()))

    if divergence_profile:
        # Variance-weighted: score = Σ(sim × divergence) / Σ(divergence)
        weighted_sum = 0.0
        total_weight = 0.0
        for space, sim in per_space_sims.items():
            if space == 'default':
                # Default always gets weight 1.0 (it's the reference, not a field)
                weighted_sum += sim * 1.0
                total_weight += 1.0
            else:
                div = divergence_profile.get(space, 0.0)
                if div > 0:
                    weighted_sum += sim * div
                    total_weight += div
        if total_weight == 0.0:
            return 0.0
        return weighted_sum / total_weight

    # Fallback: equal weighting over present spaces
    return sum(per_space_sims.values()) / len(per_space_sims)


# --- Embedding + divergence (shared by the hook, the backfill, and tests) ---

def _cos(a, b):
    """Cosine similarity of two equal-length float sequences. 0.0 if degenerate."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


def compute_divergence_profile(embeddings, round_ndigits=4):
    """Cosine *distance* of each non-default space from 'default'.

    embeddings: dict {space_name -> vector}; must contain a non-empty 'default'.
    Returns {space_name -> round(1 - cos(default, space), 4)} for every non-default
    space with a non-empty vector. Returns {} if there is no usable 'default'.

    This is the canonical implementation — it matches the math previously inlined
    in hook-post-write.sh so hook-written and backfilled profiles are identical.
    """
    default_vec = embeddings.get('default')
    if not default_vec:
        return {}
    profile = {}
    for space, vec in embeddings.items():
        if space != 'default' and vec:
            profile[space] = round(1.0 - _cos(default_vec, vec), round_ndigits)
    return profile


def embed_all_spaces(entry, config=None, embed_fn=None, max_chars=2000):
    """Embed an entry across all registered spaces.

    Returns (embeddings, divergence_profile):
      - embeddings: {space_name -> vector}, always including 'default', plus each
        field space whose composed text is non-empty (structural absence skipped).
      - divergence_profile: computed via compute_divergence_profile.
    Returns ({}, {}) if the entry has no embeddable 'default' text.

    embed_fn(text) -> vector lets tests inject a deterministic embedder; by default
    it uses memoryschema.embeddings.embed_text(text, config=config).
    """
    if embed_fn is None:
        from memoryschema.embeddings import embed_text
        def embed_fn(text):
            return embed_text(text, config=config)

    default_text = compose_embedding_text(entry, space='default', max_chars=max_chars)
    if not default_text:
        return {}, {}

    embeddings = {'default': embed_fn(default_text)}
    for space in get_registry():
        if space == 'default':
            continue
        text = compose_embedding_text(entry, space=space, max_chars=max_chars)
        if text:
            embeddings[space] = embed_fn(text)

    return embeddings, compute_divergence_profile(embeddings)
