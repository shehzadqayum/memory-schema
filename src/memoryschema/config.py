"""
Centralized configuration for the memory system.

All environment variables, defaults, and path resolution live here.
No other module in the package reads os.environ directly.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MemoryConfig:
    """Configuration for a memory system instance.

    Reads from environment variables with sensible defaults.
    All paths are resolved to absolute Path objects on init.

    Environment variables:
        NEO4J_URI       Neo4j Bolt URI (default: bolt://localhost:7687)
        NEO4J_USER      Neo4j username (default: neo4j)
        NEO4J_PASSWORD  Neo4j password (default: changeme)
        VOYAGE_API_KEY  Voyage AI API key (required for embeddings)
    """

    # Project identity
    project_name: str = "default"
    project_root: Path = field(default_factory=lambda: Path.cwd())

    # JSONL store (L1b)
    store_path: Path | None = None

    # Neo4j (L2b)
    neo4j_uri: str = field(
        default_factory=lambda: os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    )
    neo4j_user: str = field(
        default_factory=lambda: os.environ.get("NEO4J_USER", "neo4j")
    )
    neo4j_password: str = field(
        default_factory=lambda: os.environ.get("NEO4J_PASSWORD", "changeme")
    )
    neo4j_container_name: str | None = None
    neo4j_http_port: int = 7474
    neo4j_bolt_port: int = 7687

    # Voyage AI embeddings (L2a)
    voyage_api_key: str | None = field(
        default_factory=lambda: os.environ.get("VOYAGE_API_KEY")
    )
    embed_model: str = "voyage-4-lite"
    embed_dimensions: int = 1024
    rerank_model: str = "rerank-2"

    # Schema
    schema_version: int = 2
    valid_types: tuple = ("semantic", "episodic", "procedural")
    valid_relation_types: tuple = (
        "USES", "MODIFIES", "SUPERSEDES", "DEPENDS_ON", "INFORMS", "CONTRADICTS",
        "PARENT_OF", "CHILD_OF",
    )

    # Retrieval
    recency_decay: float = 0.995
    association_k: int = 10
    recall_depth: int = 2
    recall_decay: float = 0.8

    def __post_init__(self):
        self.project_root = Path(self.project_root).resolve()
        if self.store_path is None:
            self.store_path = self.project_root / "memory" / "store.jsonl"
        else:
            self.store_path = Path(self.store_path).resolve()
        if self.neo4j_container_name is None:
            self.neo4j_container_name = f"{self.project_name}-neo4j"

    @property
    def memory_dir(self) -> Path:
        """Directory for memory entity files."""
        return self.project_root / "memory"

    @property
    def memory_index_path(self) -> Path:
        """Path to MEMORY.md (L0 always-in-context index)."""
        return self.memory_dir / "MEMORY.md"

    @property
    def docker_compose_path(self) -> Path:
        """Path to docker-compose.yml."""
        return self.project_root / "docker-compose.yml"

    @property
    def rules_dir(self) -> Path:
        """Path to .claude/rules/ directory."""
        return self.project_root / ".claude" / "rules"

    @property
    def env_example_path(self) -> Path:
        """Path to .env.example."""
        return self.project_root / ".env.example"

    @property
    def config_file_path(self) -> Path:
        """Path to memoryschema.toml."""
        return self.project_root / "memoryschema.toml"

    @classmethod
    def from_toml(cls, project_root, cli_overrides=None):
        """Create config with TOML file + inheritance chain.

        Resolution order (highest to lowest):
        1. Environment variables
        2. cli_overrides dict
        3. Parent memoryschema.toml (wins over child on conflict)
        4. Child memoryschema.toml
        5. Dataclass defaults
        """
        from memoryschema.inheritance import resolve_config_chain
        resolved = resolve_config_chain(Path(project_root).resolve(), cli_overrides)
        # Convert store_path to Path if present as string
        if 'store_path' in resolved and isinstance(resolved['store_path'], str):
            resolved['store_path'] = Path(project_root) / resolved['store_path']
        return cls(**{k: v for k, v in resolved.items()
                      if k in cls.__dataclass_fields__})

    @property
    def project_segments(self) -> list[str]:
        """Split project_name into hierarchy segments."""
        from memoryschema.hierarchy import parse_project_path
        return parse_project_path(self.project_name)

    @property
    def parent_project_name(self) -> str | None:
        """Parent project name, or None if root."""
        from memoryschema.hierarchy import parent_project
        return parent_project(self.project_name)
