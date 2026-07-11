"""Tests for Neo4j store (mocked + optional integration).

Mocked tests run in standard pytest. Integration tests require a running
Neo4j instance and are skipped by default (run with: pytest -m integration).
"""

import os
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from memoryschema.config import MemoryConfig


def _make_mock_driver():
    """Create a mock Neo4j driver with session support."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return driver, session


@pytest.fixture
def mock_neo4j():
    """Patch neo4j.GraphDatabase.driver."""
    driver, session = _make_mock_driver()
    with patch("memoryschema.neo4j_store.GraphDatabase") as mock_gd:
        mock_gd.driver.return_value = driver
        yield driver, session, mock_gd


class TestInit:
    def test_default_connection(self, mock_neo4j):
        driver, session, mock_gd = mock_neo4j
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        mock_gd.driver.assert_called_once()

    def test_config_params(self, mock_neo4j):
        driver, session, mock_gd = mock_neo4j
        from memoryschema.neo4j_store import Neo4jMemoryStore
        config = MemoryConfig(neo4j_uri="bolt://custom:7687", neo4j_user="admin", neo4j_password="secret")
        store = Neo4jMemoryStore(config=config)
        call_args = mock_gd.driver.call_args
        assert "bolt://custom:7687" in str(call_args)

    def test_explicit_params(self, mock_neo4j):
        driver, session, mock_gd = mock_neo4j
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore(uri="bolt://explicit:7687", user="u", password="p")
        call_args = mock_gd.driver.call_args
        assert "bolt://explicit:7687" in str(call_args)


class TestAuthErrorHandling:
    def test_auth_error_raises_connection_error(self):
        """Auth failure produces a helpful ConnectionError, not raw Neo4j error."""
        from memoryschema.neo4j_store import Neo4jMemoryStore
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception(
            "Neo.ClientError.Security.Unauthorized: authentication failure"
        )
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("memoryschema.neo4j_store.GraphDatabase") as mock_gd:
            mock_gd.driver.return_value = mock_driver
            with pytest.raises(ConnectionError, match="NEO4J_PASSWORD"):
                Neo4jMemoryStore(uri="bolt://localhost:7687", user="neo4j", password="wrong")

    def test_non_auth_error_reraises(self):
        """Non-auth errors re-raise as-is, not wrapped in ConnectionError."""
        from memoryschema.neo4j_store import Neo4jMemoryStore
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.side_effect = RuntimeError("connection refused")
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("memoryschema.neo4j_store.GraphDatabase") as mock_gd:
            mock_gd.driver.return_value = mock_driver
            with pytest.raises(RuntimeError, match="connection refused"):
                Neo4jMemoryStore(uri="bolt://localhost:7687", user="neo4j", password="x")


class TestCRUD:
    def test_upsert(self, mock_neo4j):
        driver, session, _ = mock_neo4j
        session.run.return_value = MagicMock(single=MagicMock(return_value={"m": {}}))
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        # Mock get() for return value
        with patch.object(store, 'get', return_value={'name': 'test', 'description': 'hello'}):
            result = store.upsert({'name': 'test', 'schema': 2, 'description': 'hello'})
        assert result['name'] == 'test'

    def test_exists(self, mock_neo4j):
        driver, session, _ = mock_neo4j
        session.run.return_value = MagicMock(single=MagicMock(return_value={'exists': True}))
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        assert store.exists('test') is True

    def test_count(self, mock_neo4j):
        driver, session, _ = mock_neo4j
        session.run.return_value = MagicMock(single=MagicMock(return_value={'n': 42}))
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        assert store.count() == 42

    def test_delete(self, mock_neo4j):
        driver, session, _ = mock_neo4j
        session.run.return_value = MagicMock(single=MagicMock(return_value={'deleted': 1}))
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        assert store.delete('test') is True

    def test_close(self, mock_neo4j):
        driver, session, _ = mock_neo4j
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        store.close()
        driver.close.assert_called_once()


class TestScoring:
    def test_cosine_similarity_identical(self):
        from memoryschema.neo4j_store import _cosine_similarity
        assert abs(_cosine_similarity([1, 0], [1, 0]) - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        from memoryschema.neo4j_store import _cosine_similarity
        assert abs(_cosine_similarity([1, 0], [0, 1])) < 0.001

    def test_cosine_similarity_zero(self):
        from memoryschema.neo4j_store import _cosine_similarity
        assert _cosine_similarity([0, 0], [1, 1]) == 0.0

    def test_score_entry(self, mock_neo4j):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        entry = {'name': 'test', 'importance': 8}
        score = store._score_entry(entry)
        assert 0.0 <= score <= 1.0

    def test_score_entry_high_importance(self, mock_neo4j):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        low = store._score_entry({'name': 'low', 'importance': 1})
        high = store._score_entry({'name': 'high', 'importance': 10})
        assert high > low

    def test_searchable_text(self, mock_neo4j):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        entry = {'name': 'test', 'description': 'Hello', 'observations': ['Fact'], 'prompt': 'Q', 'reasoning': 'R'}
        text = store._searchable_text(entry)
        assert 'hello' in text
        assert 'fact' in text
        assert 'q' in text


class TestNodeConversion:
    def test_node_to_dict(self, mock_neo4j):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        node = {'name': 'test', 'description': 'Hello', 'observations': ['a', 'b'], 'observations_text': 'a b'}
        result = store._node_to_dict(node)
        assert result['name'] == 'test'
        assert result['observations'] == ['a', 'b']
        assert 'observations_text' not in result
        assert result['relations'] == []
        assert result['backlinks'] == []

    def test_node_to_dict_null_observations(self, mock_neo4j):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        node = {'name': 'test', 'observations': None}
        result = store._node_to_dict(node)
        assert result['observations'] == []


# --- Integration tests (require running Neo4j) ---

def _neo4j_available():
    """Check if Neo4j is reachable with current credentials."""
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        store.count()
        store.close()
        return True
    except Exception:
        return False


@pytest.mark.integration
class TestNeo4jIntegration:
    """Integration tests against a real Neo4j instance.

    Skipped by default. Run with: pytest -m integration
    Requires NEO4J_PASSWORD set and container running.
    """

    @pytest.fixture(autouse=True)
    def skip_if_unavailable(self):
        if not _neo4j_available():
            pytest.skip("Neo4j not available (set NEO4J_PASSWORD and start container)")

    def test_connect_and_count(self):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        count = store.count()
        assert isinstance(count, int)
        assert count >= 0
        store.close()

    def test_upsert_get_roundtrip(self):
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        test_name = '_integration_test_entry'

        try:
            store.upsert({
                'name': test_name,
                'schema': 4,
                'type': 'semantic',
                'description': 'Integration test entry — safe to delete',
                'observations': ['Test observation'],
                'importance': 1,
            })

            result = store.get(test_name)
            assert result is not None
            assert result['name'] == test_name
            assert result['description'] == 'Integration test entry — safe to delete'
            assert 'Test observation' in [str(o) for o in result.get('observations', [])]
        finally:
            # Clean up
            store.delete(test_name)
            assert store.get(test_name) is None
            store.close()

    def test_observations_append_to_null_observations_node(self):
        # Regression: a node whose observations property is NULL (e.g. created as a
        # bare relation-MERGE stub) must still accept observations on upsert. Before the
        # coalesce(m.observations, []) fix, [x WHERE NOT x IN null] filtered everything out
        # and observations could never be added to such a node.
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        test_name = '_integration_null_obs_entry'
        try:
            with store._driver.session() as s:
                s.run("CREATE (m:Memory {name:$n})", n=test_name)  # bare node → observations is null
            store.upsert({'name': test_name, 'schema': 4, 'type': 'semantic',
                          'description': 'null-obs regression', 'importance': 1,
                          'observations': ['alpha obs', 'beta obs']})
            obs = [str(o) for o in store.get(test_name).get('observations', [])]
            assert 'alpha obs' in obs and 'beta obs' in obs
        finally:
            store.delete(test_name)
            store.close()

    def test_supersedes_cycle_not_persisted(self):
        # R7: a SUPERSEDES cycle must be REJECTED WITHOUT persisting the poison edge — the check now runs
        # BEFORE the MERGE (matching the JSONL store). Regression for the old check-after-commit bug, where
        # the edge was committed and then the raise left it in the graph.
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        a, b = '_integration_cycle_a', '_integration_cycle_b'
        try:
            store.delete(a)
            store.delete(b)
            store.upsert({'name': b, 'schema': 5, 'type': 'semantic', 'description': 'cycle b', 'importance': 1})
            store.upsert({'name': a, 'schema': 5, 'type': 'semantic', 'description': 'cycle a',
                          'importance': 1, 'relations': [{'type': 'SUPERSEDES', 'target': b}]})   # a -> b, ok
            with pytest.raises(ValueError, match="cycle"):
                store.upsert({'name': b, 'schema': 5, 'type': 'semantic', 'description': 'cycle b',
                              'importance': 1, 'relations': [{'type': 'SUPERSEDES', 'target': a}]})  # b->a cycles
            with store._driver.session() as s:
                back = s.run("MATCH (:Memory {name:$b})-[r:SUPERSEDES]->(:Memory {name:$a}) RETURN count(r) AS c",
                             a=a, b=b).single()['c']
                fwd = s.run("MATCH (:Memory {name:$a})-[r:SUPERSEDES]->(:Memory {name:$b}) RETURN count(r) AS c",
                            a=a, b=b).single()['c']
            assert back == 0, "the cyclic SUPERSEDES edge must NOT be persisted"
            assert fwd == 1, "the legit a->b edge must remain"
        finally:
            store.delete(a)
            store.delete(b)
            store.close()

    def test_multispace_roundtrip(self):
        # Per-space embeddings + divergence persist and reconstruct on read.
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore()
        test_name = '_integration_multispace_entry'
        try:
            store.upsert({'name': test_name, 'schema': 4, 'type': 'semantic',
                          'description': 'multispace roundtrip', 'importance': 1,
                          'embedding': [1.0, 0.0],
                          'embeddings': {'default': [1.0, 0.0], 'observations': [0.0, 1.0]},
                          'divergence_profile': {'observations': 0.9}})
            result = store.get(test_name)
            assert set(result.get('embeddings', {}).keys()) == {'default', 'observations'}
            assert result.get('divergence_profile') == {'observations': 0.9}
        finally:
            store.delete(test_name)
            store.close()
