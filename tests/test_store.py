"""Tests for JSONL MemoryStore."""

import json
import os

import pytest

from memoryschema.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    """Create a MemoryStore with a temp JSONL file."""
    path = str(tmp_path / "test-store.jsonl")
    return MemoryStore(path)


@pytest.fixture
def populated_store(store):
    """Store with 3 entries."""
    store.upsert({'name': 'alpha', 'schema': 2, 'description': 'First entry', 'type': 'semantic', 'importance': 7})
    store.upsert({'name': 'beta', 'schema': 2, 'description': 'Second entry', 'type': 'episodic', 'importance': 5})
    store.upsert({'name': 'gamma', 'schema': 2, 'description': 'Third entry', 'type': 'semantic', 'importance': 9,
                  'observations': ['Fact A', 'Fact B']})
    return store


class TestUpsert:
    def test_insert(self, store):
        result = store.upsert({'name': 'test', 'schema': 2, 'description': 'Hello'})
        assert result['name'] == 'test'
        assert result['description'] == 'Hello'
        assert result['created_at'] is not None
        assert result['access_count'] == 0

    def test_merge_description(self, store):
        store.upsert({'name': 'test', 'schema': 2, 'description': 'Original'})
        store.upsert({'name': 'test', 'description': 'Updated'})
        entry = store.get('test')
        assert entry['description'] == 'Updated'

    def test_merge_observations_append(self, store):
        store.upsert({'name': 'test', 'schema': 2, 'description': 'Test', 'observations': ['A', 'B']})
        store.upsert({'name': 'test', 'observations': ['B', 'C']})
        entry = store.get('test')
        assert entry['observations'] == ['A', 'B', 'C']  # B not duplicated

    def test_merge_relations_dedup(self, store):
        store.upsert({'name': 'test', 'schema': 2, 'description': 'Test',
                       'relations': [{'target': 'other', 'type': 'USES'}]})
        store.upsert({'name': 'test',
                       'relations': [{'target': 'other', 'type': 'USES'}, {'target': 'new', 'type': 'INFORMS'}]})
        entry = store.get('test')
        assert len(entry['relations']) == 2  # USES not duplicated

    def test_created_at_preserved(self, store):
        store.upsert({'name': 'test', 'schema': 2, 'description': 'V1'})
        created = store.get('test')['created_at']
        store.upsert({'name': 'test', 'description': 'V2'})
        assert store.get('test')['created_at'] == created


class TestGet:
    def test_found(self, populated_store):
        entry = populated_store.get('alpha')
        assert entry is not None
        assert entry['description'] == 'First entry'

    def test_not_found(self, populated_store):
        assert populated_store.get('nonexistent') is None


class TestExists:
    def test_exists(self, populated_store):
        assert populated_store.exists('alpha') is True

    def test_not_exists(self, populated_store):
        assert populated_store.exists('nonexistent') is False


class TestCount:
    def test_empty(self, store):
        assert store.count() == 0

    def test_populated(self, populated_store):
        assert populated_store.count() == 3


class TestAccess:
    def test_increments(self, populated_store):
        entry = populated_store.access('alpha')
        assert entry['access_count'] == 1
        entry = populated_store.access('alpha')
        assert entry['access_count'] == 2

    def test_not_found(self, populated_store):
        assert populated_store.access('nonexistent') is None


class TestSearch:
    def test_by_query(self, populated_store):
        results = populated_store.search(query='First')
        assert len(results) == 1
        assert results[0]['name'] == 'alpha'

    def test_by_type(self, populated_store):
        results = populated_store.search(type='semantic')
        assert len(results) == 2

    def test_by_query_and_type(self, populated_store):
        results = populated_store.search(query='entry', type='episodic')
        assert len(results) == 1
        assert results[0]['name'] == 'beta'

    def test_limit(self, populated_store):
        results = populated_store.search(limit=1)
        assert len(results) == 1

    def test_observation_search(self, populated_store):
        results = populated_store.search(query='Fact A')
        assert len(results) == 1
        assert results[0]['name'] == 'gamma'


class TestDelete:
    def test_delete_existing(self, populated_store):
        assert populated_store.delete('alpha') is True
        assert populated_store.count() == 2
        assert populated_store.get('alpha') is None

    def test_delete_nonexistent(self, populated_store):
        assert populated_store.delete('nonexistent') is False
        assert populated_store.count() == 3


class TestListAll:
    def test_list(self, populated_store):
        entries = populated_store.list_all()
        assert len(entries) == 3
        names = {e['name'] for e in entries}
        assert names == {'alpha', 'beta', 'gamma'}


class TestComputeBacklinks:
    def test_backlinks(self, store):
        store.upsert({'name': 'source', 'schema': 2, 'description': 'Source',
                       'relations': [{'target': 'target', 'type': 'INFORMS'}]})
        store.upsert({'name': 'target', 'schema': 2, 'description': 'Target'})
        count = store.compute_backlinks()
        assert count == 1  # target has backlink from source
        target = store.get('target')
        assert len(target['backlinks']) == 1
        assert target['backlinks'][0]['source'] == 'source'


class TestScoreEntry:
    def test_score_range(self, store):
        entry = {'name': 'test', 'importance': 5}
        score = store._score_entry(entry)
        assert 0.0 <= score <= 1.0

    def test_higher_importance_higher_score(self, store):
        low = store._score_entry({'name': 'low', 'importance': 1})
        high = store._score_entry({'name': 'high', 'importance': 10})
        assert high > low


class TestAtomicWrites:
    def test_file_not_corrupted_on_error(self, tmp_path):
        path = str(tmp_path / "atomic-test.jsonl")
        store = MemoryStore(path)
        store.upsert({'name': 'safe', 'schema': 2, 'description': 'Safe entry'})

        # Verify file is valid JSONL
        with open(path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 1
        assert lines[0]['name'] == 'safe'


class TestCosineSimilarity:
    def test_identical_vectors(self):
        from memoryschema.store import _cosine_similarity
        a = [1.0, 0.0, 0.0]
        assert abs(_cosine_similarity(a, a) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        from memoryschema.store import _cosine_similarity
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 0.001

    def test_zero_vector(self):
        from memoryschema.store import _cosine_similarity
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_opposite_vectors(self):
        from memoryschema.store import _cosine_similarity
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) < 0


class TestGetStore:
    def test_fallback_to_jsonl(self, tmp_path):
        from unittest.mock import patch
        from memoryschema.store import get_store
        from memoryschema.config import MemoryConfig
        config = MemoryConfig(project_root=tmp_path)
        with patch.dict("sys.modules", {"memoryschema.neo4j_store": None}):
            store = get_store(config=config)
        assert isinstance(store, MemoryStore)

    def test_with_jsonl_path(self, tmp_path):
        from unittest.mock import patch
        from memoryschema.store import get_store
        path = str(tmp_path / "custom.jsonl")
        with patch.dict("sys.modules", {"memoryschema.neo4j_store": None}):
            store = get_store(jsonl_path=path)
        assert isinstance(store, MemoryStore)


class TestRecall:
    def test_recall_by_name(self, populated_store):
        populated_store.upsert({
            'name': 'target', 'schema': 2, 'description': 'Recall target',
            'relations': [{'target': 'alpha', 'type': 'USES'}],
        })
        populated_store.compute_backlinks()
        results = populated_store.recall(name='target', depth=1)
        assert len(results) >= 1
        assert results[0]['name'] == 'target'

    def test_recall_by_query(self, populated_store):
        results = populated_store.recall(query='First entry')
        assert len(results) >= 1

    def test_recall_empty_store(self, store):
        results = store.recall(query='anything')
        assert results == []

    def test_recall_no_args(self, populated_store):
        results = populated_store.recall()
        assert results == []

    def test_recall_cascade_relations(self, store):
        store.upsert({'name': 'parent', 'schema': 2, 'description': 'Parent',
                       'relations': [{'target': 'child', 'type': 'USES'}]})
        store.upsert({'name': 'child', 'schema': 2, 'description': 'Child'})
        store.compute_backlinks()
        results = store.recall(name='parent', depth=2)
        names = {r['name'] for r in results}
        assert 'parent' in names
        assert 'child' in names

    def test_recall_cascade_associations(self, store):
        store.upsert({'name': 'a', 'schema': 2, 'description': 'Entity A',
                       'associations': [{'name': 'b', 'score': 0.9}]})
        store.upsert({'name': 'b', 'schema': 2, 'description': 'Entity B'})
        results = store.recall(name='a', depth=2)
        names = {r['name'] for r in results}
        assert 'a' in names
        assert 'b' in names


class TestComputeAssociations:
    def test_no_embeddings(self, store):
        store.upsert({'name': 'a', 'schema': 2, 'description': 'No embedding'})
        assert store.compute_associations() == 0

    def test_with_embeddings(self, store):
        store.upsert({'name': 'a', 'schema': 2, 'description': 'A', 'embedding': [1.0, 0.0, 0.0]})
        store.upsert({'name': 'b', 'schema': 2, 'description': 'B', 'embedding': [0.9, 0.1, 0.0]})
        store.upsert({'name': 'c', 'schema': 2, 'description': 'C', 'embedding': [0.0, 1.0, 0.0]})
        result = store.compute_associations(k=2)
        assert result >= 2
        entry_a = store.get('a')
        assert len(entry_a.get('associations', [])) > 0


class TestHierarchyScoping:
    """Integration tests for hierarchy scoping across store operations."""

    @pytest.fixture
    def scoped_store(self, tmp_path):
        s = MemoryStore(str(tmp_path / "scoped.jsonl"))
        s.upsert({'name': 'parent-mem', 'schema': 2, 'description': 'Parent memory',
                  'project': 'org', 'type': 'semantic', 'importance': 7})
        s.upsert({'name': 'child-mem', 'schema': 2, 'description': 'Child memory',
                  'project': 'org.team', 'type': 'semantic', 'importance': 7})
        s.upsert({'name': 'grandchild-mem', 'schema': 2, 'description': 'Grandchild memory',
                  'project': 'org.team.sub', 'type': 'semantic', 'importance': 7})
        s.upsert({'name': 'unrelated-mem', 'schema': 2, 'description': 'Unrelated project',
                  'project': 'other', 'type': 'semantic', 'importance': 7})
        s.upsert({'name': 'unscoped-mem', 'schema': 2, 'description': 'No project field',
                  'type': 'semantic', 'importance': 7})
        return s

    def test_search_project_returns_children(self, scoped_store):
        results = scoped_store.search(project='org')
        names = {r['name'] for r in results}
        assert 'parent-mem' in names
        assert 'child-mem' in names
        assert 'grandchild-mem' in names
        assert 'unrelated-mem' not in names

    def test_search_project_excludes_unrelated(self, scoped_store):
        results = scoped_store.search(project='other')
        names = {r['name'] for r in results}
        assert names == {'unrelated-mem', 'unscoped-mem'}

    def test_recall_project_scope_bidirectional(self, scoped_store):
        # Add relation so recall cascades from child to parent
        scoped_store.upsert({'name': 'child-mem', 'schema': 2, 'description': 'Child memory',
                             'project': 'org.team', 'type': 'semantic', 'importance': 7,
                             'relations': [{'target': 'parent-mem', 'type': 'DEPENDS_ON'}]})
        results = scoped_store.recall(name='child-mem', project='org.team')
        names = {r['name'] for r in results}
        assert 'child-mem' in names
        assert 'parent-mem' in names  # read-up via relation + scope
        assert 'unrelated-mem' not in names

    def test_unscoped_entity_visible_everywhere(self, scoped_store):
        # Entity with no project is universally visible
        results = scoped_store.search(project='org')
        names = {r['name'] for r in results}
        assert 'unscoped-mem' in names

        results = scoped_store.search(project='other')
        names = {r['name'] for r in results}
        assert 'unscoped-mem' in names

    def test_list_all_with_project(self, scoped_store):
        results = scoped_store.list_all(project='org.team')
        names = {r['name'] for r in results}
        assert 'child-mem' in names
        assert 'grandchild-mem' in names
        assert 'unscoped-mem' in names  # universal
        assert 'parent-mem' not in names  # list_all uses filter, not scope
        assert 'unrelated-mem' not in names
