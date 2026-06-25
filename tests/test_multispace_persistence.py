"""Tests for multi-space embedding activation: divergence computation, the
embed-all-spaces helper, Neo4j per-space (de)serialization, JSONL merge
preservation, and the shared module-level relevance wrapper.

All hermetic — pure functions + a tmp_path JSONL store; no live Neo4j/Voyage
(the autouse conftest fixture strips those env vars for non-integration tests).
"""

from memoryschema import spaces
from memoryschema import neo4j_store as ns
from memoryschema.store import MemoryStore, multi_space_relevance


# --- compute_divergence_profile ---

class TestDivergenceProfile:
    def test_identical_space_zero_orthogonal_one(self):
        embs = {
            'default': [1.0, 0.0, 0.0],
            'name': [1.0, 0.0, 0.0],        # identical → divergence 0
            'observations': [0.0, 1.0, 0.0],  # orthogonal → divergence 1
        }
        prof = spaces.compute_divergence_profile(embs)
        assert prof['name'] == 0.0
        assert prof['observations'] == 1.0
        assert 'default' not in prof  # default is the reference, never in the profile

    def test_no_default_returns_empty(self):
        assert spaces.compute_divergence_profile({'name': [1.0, 0.0]}) == {}

    def test_rounding(self):
        prof = spaces.compute_divergence_profile(
            {'default': [1.0, 0.0], 'name': [0.9, 0.1]})
        assert prof['name'] == round(prof['name'], 4)


# --- embed_all_spaces ---

class TestEmbedAllSpaces:
    def test_skips_empty_fields_and_includes_default(self):
        entry = {'name': 'x', 'description': 'd',
                 'observations': ['o1'], 'prompt': '', 'reasoning': ''}
        embs, div = spaces.embed_all_spaces(entry, embed_fn=lambda t: [1.0, 0.0])
        # default + name + description + observations present; empty prompt/reasoning/chain skipped
        assert set(embs.keys()) == {'default', 'name', 'description', 'observations'}
        assert 'prompt' not in embs and 'reasoning' not in embs and 'chain' not in embs
        # divergence keyed on non-default present spaces
        assert set(div.keys()) == {'name', 'description', 'observations'}

    def test_empty_default_returns_empty(self):
        embs, div = spaces.embed_all_spaces({}, embed_fn=lambda t: [1.0])
        assert embs == {} and div == {}


# --- Neo4j per-space (de)serialization ---

class TestNeo4jMultispaceSerde:
    def test_roundtrip(self):
        md = {'embeddings': {'default': [1.0, 0.0], 'name': [0.0, 1.0],
                             'observations': [1.0, 1.0]},
              'divergence_profile': {'name': 0.5, 'observations': 0.1}}
        props = ns._serialize_multispace(md)
        # present field spaces carry vectors; absent ones are None (clears stale on re-upsert)
        assert props['emb_name'] == [0.0, 1.0]
        assert props['emb_observations'] == [1.0, 1.0]
        assert props['emb_prompt'] is None and props['emb_reasoning'] is None
        # simulate the node read shape: default in 'embedding', field spaces in emb_*
        node = {'embedding': md['embeddings']['default'],
                'emb_name': props['emb_name'],
                'emb_observations': props['emb_observations'],
                'divergence_profile_json': props['divergence_profile_json']}
        ns._deserialize_multispace(node)
        assert set(node['embeddings'].keys()) == {'default', 'name', 'observations'}
        assert node['divergence_profile'] == {'name': 0.5, 'observations': 0.1}
        # raw columns stripped so they don't leak into the entry / JSONL export
        assert 'emb_name' not in node and 'divergence_profile_json' not in node

    def test_no_embeddings_returns_none(self):
        assert ns._serialize_multispace({'name': 'y'}) is None

    def test_default_only_keeps_single_embedding_path(self):
        # a node with only the default vector should NOT expose a multi-space dict
        node = {'embedding': [1.0, 0.0]}
        ns._deserialize_multispace(node)
        assert 'embeddings' not in node

    def test_field_space_without_default_is_exposed(self):
        # MINOR-2: a node with a field space but no default vector must still expose embeddings
        # (previously dropped because the guard required len(embeddings) > 1).
        node = {'name': 'x', 'emb_observations': [0.0, 1.0]}
        ns._deserialize_multispace(node)
        assert node.get('embeddings') == {'observations': [0.0, 1.0]}


# --- JSONL merge preserves multi-space across re-upsert ---

class TestJsonlMergePreservesMultispace:
    def test_merge_keeps_and_updates_multispace(self, tmp_path):
        store = MemoryStore(str(tmp_path / 'store.jsonl'))
        store.upsert({'name': 'm', 'description': 'd1', 'embedding': [1.0, 0.0],
                      'embeddings': {'default': [1.0, 0.0], 'name': [0.0, 1.0]},
                      'divergence_profile': {'name': 0.5}})
        # re-upsert (merge path) with an edited field + an added space
        store.upsert({'name': 'm', 'description': 'd2',
                      'embedding': [1.0, 0.0],
                      'embeddings': {'default': [1.0, 0.0], 'name': [0.0, 1.0],
                                     'observations': [1.0, 1.0]},
                      'divergence_profile': {'name': 0.5, 'observations': 0.2}})
        got = store.get('m')
        assert got['description'] == 'd2'
        assert set(got['embeddings'].keys()) == {'default', 'name', 'observations'}
        assert got['divergence_profile']['observations'] == 0.2


# --- shared module-level relevance wrapper ---

class TestMultiSpaceRelevanceWrapper:
    def test_single_embedding_fallback(self):
        r = multi_space_relevance({'embedding': [1.0, 0.0]}, [1.0, 0.0])
        assert round(r, 3) == 1.0

    def test_multi_space_uses_divergence(self):
        # query matches the high-divergence 'observations' space strongly
        entry = {'embeddings': {'default': [1.0, 0.0], 'observations': [0.0, 1.0]},
                 'divergence_profile': {'observations': 1.0}}
        r = multi_space_relevance(entry, [0.0, 1.0])
        # default sim 0, observations sim 1 with weight 1.0; default pinned weight 1.0
        # → (0*1 + 1*1)/(1+1) = 0.5
        assert round(r, 3) == 0.5
