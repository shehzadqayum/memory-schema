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
