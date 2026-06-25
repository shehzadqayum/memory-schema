"""End-to-end pipeline tests: write -> gate -> store -> recall.

Exercises the full memory write pipeline in a single test flow.
Embeddings are mocked (deterministic vectors) — no Voyage API needed.
Includes hook pipeline integration tests (Phase 5).
"""

import json
import os
from unittest.mock import patch

import pytest

from memoryschema.config import MemoryConfig
from memoryschema.store import MemoryStore
from memoryschema.write_gate import gate_pipeline, GateVerdict


# Deterministic 10-dim vectors for testing
_VEC_A = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
_VEC_B = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / 'store.jsonl'))


@pytest.fixture
def config(tmp_path):
    return MemoryConfig(store_path=str(tmp_path / 'store.jsonl'))


class TestWriteGateStoreRecall:
    """Full pipeline: gate -> store -> recall in one flow."""

    def test_accept_store_recall(self, store, config):
        """ACCEPT -> upsert -> recall finds the entry."""
        memory = {
            'name': 'test-fact',
            'schema': 4,
            'type': 'semantic',
            'description': 'A test fact about architecture',
            'observations': ['The system uses JSONL storage'],
            'importance': 7,
        }

        # Gate: should accept a valid entry
        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT

        # Store: upsert the accepted entry
        store.upsert(memory)
        stored = store.get('test-fact')
        assert stored is not None
        assert stored['description'] == 'A test fact about architecture'

        # Recall: find it by text search (no embeddings needed for BM25)
        results = store.recall(query='architecture')
        names = [r['name'] for r in results]
        assert 'test-fact' in names

    def test_reject_never_stored(self, store, config):
        """REJECT -> entry never reaches the store."""
        memory = {
            # Missing 'name' — should be rejected
            'schema': 4,
            'description': 'No name provided',
        }

        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.REJECT

        # Store should be empty
        assert store.count() == 0

    def test_accept_with_embedding_recall(self, store, config):
        """Full path with mocked embeddings: embed -> store -> recall by vector."""
        memory = {
            'name': 'embedded-fact',
            'schema': 4,
            'type': 'semantic',
            'description': 'A fact with embedding',
            'importance': 8,
        }

        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT

        # Add embedding manually (simulating what the hook does)
        memory['embedding'] = _VEC_A
        store.upsert(memory)

        # Recall with mocked query embedding
        with patch('memoryschema.embeddings.embed_text', return_value=_VEC_A):
            results = store.recall(query='fact with embedding')
        names = [r['name'] for r in results]
        assert 'embedded-fact' in names


class TestRelationCascade:
    """Test recall traversal through relations and backlinks."""

    def test_backlink_recall(self, store):
        """B INFORMS A -> recall A at depth=1 finds B via backlink."""
        store.upsert({
            'name': 'target-a',
            'schema': 4,
            'type': 'semantic',
            'description': 'Target entry A',
            'importance': 7,
        })
        store.upsert({
            'name': 'source-b',
            'schema': 4,
            'type': 'semantic',
            'description': 'Source entry B informs A',
            'importance': 6,
            'relations': [{'target': 'target-a', 'type': 'INFORMS'}],
        })

        store.compute_backlinks()

        # Recall by name with depth=1 should find source-b via backlink
        results = store.recall(name='target-a', depth=1)
        names = [r['name'] for r in results]
        assert 'target-a' in names
        assert 'source-b' in names
        # Verify source-b came via backlink channel
        source_result = next(r for r in results if r['name'] == 'source-b')
        assert source_result['channel'] == 'backlink'

    def test_supersedes_marks_target(self, store):
        """SUPERSEDES relation marks target as superseded."""
        store.upsert({
            'name': 'old-fact',
            'schema': 4,
            'provenance': 'first-party',
            'description': 'Old fact',
        })
        store.upsert({
            'name': 'new-fact',
            'schema': 4,
            'provenance': 'first-party',
            'description': 'New fact replaces old',
            'relations': [{'target': 'old-fact', 'type': 'SUPERSEDES'}],
        })

        old = store.get('old-fact')
        assert old['status'] == 'superseded'

        # Recall should exclude superseded by default
        results = store.recall(query='fact')
        names = [r['name'] for r in results]
        assert 'new-fact' in names
        assert 'old-fact' not in names


# --- Phase 5: Hook pipeline integration tests ---

class TestHookPipeline:
    """Replicate the hook's Python block logic as callable function calls.

    Exercises the same construction the hook uses: MemoryConfig,
    MemoryStore, gate_pipeline with store + config. Resolves session 18
    residual (E2 write path Tested but not Operative via subprocess).
    """

    def test_gate_pipeline_with_store_and_config(self, tmp_path):
        """Construct same objects as hook and run gate_pipeline — ACCEPT."""
        store_path = str(tmp_path / 'store.jsonl')
        config = MemoryConfig(project_root=str(tmp_path), store_path=store_path)
        store = MemoryStore(store_path)

        memory = {
            'name': 'hook-test-entry',
            'schema': 4,
            'description': 'Entry written through hook pipeline',
            'observations': ['Fact from hook path'],
            'importance': 6,
        }

        result = gate_pipeline(memory, store=store, config=config)
        assert result.verdict == GateVerdict.ACCEPT

        store.upsert(memory)
        stored = store.get('hook-test-entry')
        assert stored is not None
        assert stored['description'] == 'Entry written through hook pipeline'

    def test_memory_md_update_logic(self, tmp_path):
        """Replicate hook's MEMORY.md update: append, budget, categorize."""
        from memoryschema.l0_budget import enforce_budget, categorize_index

        store_path = str(tmp_path / 'store.jsonl')
        index_path = str(tmp_path / 'MEMORY.md')
        store = MemoryStore(store_path)

        # Write initial MEMORY.md
        with open(index_path, 'w') as f:
            f.write('# Memory Index\n')

        # Simulate two hook writes
        for i, entry_type in enumerate(['semantic', 'episodic']):
            name = f'hook-entry-{i}'
            memory = {
                'name': name,
                'schema': 4,
                'type': entry_type,
                'description': f'Entry {i} ({entry_type})',
            }
            store.upsert(memory)

            # Replicate hook's MEMORY.md append logic
            with open(index_path, 'r') as f:
                existing = f.read()
            if f'[{name}]' not in existing:
                entry_line = f'- [{name}]({name}.md) — Entry {i} ({entry_type})'
                existing = existing.rstrip('\n') + '\n' + entry_line + '\n'
                with open(index_path, 'w') as f:
                    f.write(existing)

        # Enforce budget (should be well under, no evictions)
        result = enforce_budget(index_path, store_path)
        assert result['evicted'] == []

        # Categorize (group by type)
        count = categorize_index(index_path, store_path)
        assert count == 2

        with open(index_path) as f:
            content = f.read()
        assert '### Knowledge' in content  # semantic
        assert '### Session History' in content  # episodic
        assert '[hook-entry-0]' in content
        assert '[hook-entry-1]' in content

    def test_neo4j_fallback_to_jsonl(self, tmp_path):
        """With Neo4j unavailable, hook falls through to JSONL upsert."""
        store_path = str(tmp_path / 'store.jsonl')
        store = MemoryStore(store_path)

        memory = {
            'name': 'fallback-entry',
            'schema': 4,
            'description': 'Entry via JSONL fallback',
        }

        # Simulate hook's fallback: Neo4j import fails → JSONL succeeds
        indexed = False
        try:
            raise ImportError("neo4j not available")
        except ImportError:
            pass

        if not indexed:
            store.upsert(memory)
            store.compute_backlinks()
            indexed = True

        assert indexed
        assert store.get('fallback-entry') is not None
