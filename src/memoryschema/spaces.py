"""Embedding space registry and combiner.

The registry is a declared catalogue of embedding spaces. Each space
defines what text gets embedded (input-selector) and how (embedder).
The combiner takes per-space similarities and returns one score.

Phase M0: ships with one space ('default') and an identity combiner.
Behavior is identical to the pre-registry system. Future phases add
field-specific spaces (observations, reasoning) gated on experiments.

Design constraints:
- A memory has n embedding spaces. Each is immutable (embed-and-freeze)
  or mutable (anchor-plus-replay). M0-M2 build immutable only.
- Mutable grounds only in immutable (no mutable-on-mutable).
- The combiner is coverage-aware: iterates only present spaces, never
  reads an absent space as zero or disagreement.
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


# Registry: default (blended) + field-level spaces
_REGISTRY = {
    'default': SpaceDefinition('default', 'immutable', 'default', 'voyage'),
    'observations': SpaceDefinition('observations', 'immutable', 'observations', 'voyage'),
    'reasoning': SpaceDefinition('reasoning', 'immutable', 'reasoning', 'voyage'),
    'description': SpaceDefinition('description', 'immutable', 'description', 'voyage'),
}


def get_registry():
    """Return the current space registry."""
    return dict(_REGISTRY)


def get_space(name):
    """Look up a space definition by name."""
    return _REGISTRY.get(name)


# --- Combiner ---

# M1 experiment: equal weighting across present spaces (no query-type
# classification). This is the unlearned heuristic — measure whether
# field separation alone helps before adding query-conditioned weights.
# None = equal weighting over present spaces (coverage-aware).
EXPERIMENT_WEIGHTS = None


def combine_similarities(per_space_sims, weights=EXPERIMENT_WEIGHTS):
    """Combine per-space similarities into a single score.

    Coverage-aware: iterates only spaces present in per_space_sims.
    Never reads an absent space as zero — corpus memories lacking
    prompt/reasoning spaces are structural, not exceptional.

    M1 experiment: weights=None (equal weighting). If the field-space
    experiment does not beat the single-space baseline, this combiner
    does not ship to default scoring.

    Args:
        per_space_sims: dict mapping space_name → similarity score.
        weights: optional dict mapping space_name → weight. If None,
            uses equal weighting over present spaces.

    Returns:
        Combined similarity score (float).
    """
    if not per_space_sims:
        return 0.0

    if weights is None:
        # Identity: if only 'default' is present, return it directly
        if 'default' in per_space_sims and len(per_space_sims) == 1:
            return per_space_sims['default']
        # Equal weighting over present spaces
        return sum(per_space_sims.values()) / len(per_space_sims)

    # Weighted combination over present spaces only
    total_weight = 0.0
    weighted_sum = 0.0
    for space, sim in per_space_sims.items():
        w = weights.get(space, 1.0)
        weighted_sum += sim * w
        total_weight += w

    if total_weight == 0.0:
        return 0.0
    return weighted_sum / total_weight
