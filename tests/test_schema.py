"""Tests for Neo4j schema setup (mocked)."""

from unittest.mock import patch, MagicMock

import pytest

from memoryschema.config import MemoryConfig


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return driver, session


class TestCreateSchema:
    def test_creates_indexes(self, mock_driver):
        driver, session = mock_driver
        from memoryschema.schema import create_schema
        create_schema(driver)
        # Should run multiple Cypher statements (constraint, vector, fulltext, range indexes)
        assert session.run.call_count >= 7  # 1 constraint + 1 vector + 1 fulltext + 4 range

    def test_idempotent(self, mock_driver):
        driver, session = mock_driver
        from memoryschema.schema import create_schema
        create_schema(driver)
        create_schema(driver)
        # Should run without error on second call


class TestVerifySchema:
    def test_returns_indexes(self, mock_driver):
        driver, session = mock_driver
        session.run.return_value = [
            {"name": "memory_name_unique", "type": "UNIQUENESS"},
            {"name": "memory_embedding", "type": "VECTOR"},
        ]
        from memoryschema.schema import verify_schema
        result = verify_schema(driver)
        assert len(result) == 2


class TestSetupSchema:
    def test_creates_driver_from_config(self):
        config = MemoryConfig(neo4j_uri="bolt://test:7687", neo4j_user="u", neo4j_password="p")
        with patch("memoryschema.schema.GraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.run.return_value = []
            mock_gd.driver.return_value = mock_driver
            from memoryschema.schema import setup_schema
            setup_schema(config)
            mock_gd.driver.assert_called_once_with("bolt://test:7687", auth=("u", "p"))
            mock_driver.close.assert_called_once()

    def test_default_config(self):
        with patch("memoryschema.schema.GraphDatabase") as mock_gd:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.run.return_value = []
            mock_gd.driver.return_value = mock_driver
            from memoryschema.schema import setup_schema
            setup_schema()
            mock_gd.driver.assert_called_once()
