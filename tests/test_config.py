"""Tests for MemoryConfig dataclass."""

import os
from pathlib import Path

import pytest

from memoryschema.config import MemoryConfig


def test_defaults():
    config = MemoryConfig()
    assert config.project_name == "default"
    assert config.neo4j_user == "neo4j"
    assert config.embed_model == "voyage-4-lite"
    assert config.embed_dimensions == 1024
    assert config.schema_version == 5   # tracks the current authored format (schema-split B4)
    assert config.association_k == 10
    assert config.recency_decay == 0.995


def test_project_name():
    config = MemoryConfig(project_name="my-project")
    assert config.project_name == "my-project"
    assert config.neo4j_container_name == "my-project-neo4j"


def test_store_path_default(tmp_path):
    config = MemoryConfig(project_root=tmp_path)
    assert config.store_path == tmp_path / "memory" / "store.jsonl"


def test_store_path_override(tmp_path):
    # Use a platform-appropriate absolute path; config resolves store_path to
    # an absolute Path on init, so compare against the same resolved path.
    custom = tmp_path / "custom" / "store.jsonl"
    config = MemoryConfig(store_path=str(custom))
    assert config.store_path == custom


def test_memory_dir(tmp_path):
    config = MemoryConfig(project_root=tmp_path)
    assert config.memory_dir == tmp_path / "memory"


def test_memory_index_path(tmp_path):
    config = MemoryConfig(project_root=tmp_path)
    assert config.memory_index_path == tmp_path / "memory" / "MEMORY.md"


def test_docker_compose_path(tmp_path):
    config = MemoryConfig(project_root=tmp_path)
    assert config.docker_compose_path == tmp_path / "docker-compose.yml"


def test_rules_dir(tmp_path):
    config = MemoryConfig(project_root=tmp_path)
    assert config.rules_dir == tmp_path / ".claude" / "rules"


def test_env_example_path(tmp_path):
    config = MemoryConfig(project_root=tmp_path)
    assert config.env_example_path == tmp_path / ".env.example"


def test_neo4j_env_override(monkeypatch):
    monkeypatch.setenv("NEO4J_URI", "bolt://custom:7687")
    monkeypatch.setenv("NEO4J_USER", "admin")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    config = MemoryConfig()
    assert config.neo4j_uri == "bolt://custom:7687"
    assert config.neo4j_user == "admin"
    assert config.neo4j_password == "secret"


def test_voyage_env(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "voy-test123")
    config = MemoryConfig()
    assert config.voyage_api_key == "voy-test123"


def test_voyage_env_missing(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    config = MemoryConfig()
    assert config.voyage_api_key is None


def test_valid_types():
    config = MemoryConfig()
    assert "semantic" in config.valid_types
    assert "episodic" in config.valid_types
    assert "procedural" in config.valid_types


def test_valid_relation_types():
    config = MemoryConfig()
    assert "USES" in config.valid_relation_types
    assert "MODIFIES" in config.valid_relation_types
    assert "SUPERSEDES" in config.valid_relation_types
    assert "DEPENDS_ON" in config.valid_relation_types
    assert "INFORMS" in config.valid_relation_types
    assert "CONTRADICTS" in config.valid_relation_types


def test_project_root_resolves():
    config = MemoryConfig(project_root=".")
    assert config.project_root.is_absolute()
