"""
Centralized configuration for the memory system.

Environment variables are read here via dataclass field defaults.
TOML inheritance is handled by inheritance.py (no env var reads there).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# Canonical constants — other modules import from here.
VALID_TYPES = frozenset({'semantic', 'episodic', 'procedural'})
VALID_STATUSES = frozenset({'active', 'superseded', 'archived', 'quarantined'})
VALID_PROVENANCES = frozenset({'first-party', 'user', 'ingested', 'derived'})
VALID_RELATION_TYPES = frozenset({
    'USES', 'MODIFIES', 'SUPERSEDES', 'DEPENDS_ON', 'INFORMS', 'CONTRADICTS',
    'MITIGATES',
})
# Deprecated in v3: hierarchy is the project field, not relation edges.
# Accepted on read for backward compatibility, warned on write.
DEPRECATED_RELATION_TYPES = frozenset({'PARENT_OF', 'CHILD_OF'})
# Combined set for validation (accepts both active and deprecated)
ALL_RELATION_TYPES = VALID_RELATION_TYPES | DEPRECATED_RELATION_TYPES
SCHEMA_VERSION = 4

# v4: basis attribute on observations — classifies how claims were obtained.
VALID_BASES = frozenset({'measured', 'inferred', 'reported'})

# Verification rank ordering for SUPERSEDES guards.
# Higher rank can supersede same or lower; lower cannot supersede higher.
VERIFICATION_RANKS = {
    'measured': 3,
    'inferred': 2,
    'reported': 1,
    None: 2,  # unlabelled = neutral rank
}

# Trust hierarchy for SUPERSEDES authority guards.
# Higher level can supersede same or lower; lower cannot supersede higher.
# derived=3 because consolidation (reflect) creates derived entries that
# legitimately supersede first-party episodic entries.
TRUST_LEVELS = {
    'user': 3,
    'first-party': 3,
    'derived': 3,
    'ingested': 1,
}


@dataclass
class MemoryConfig:
    """Configuration for a memory system instance.

    Reads from environment variables with sensible defaults.
    All paths are resolved to absolute Path objects on init.

    Environment variables:
        NEO4J_URI       Neo4j Bolt URI (default: bolt://localhost:7687)
        NEO4J_USER      Neo4j username (default: neo4j)
        NEO4J_PASSWORD  Neo4j password (no default — set via env or init)
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
        default_factory=lambda: os.environ.get("NEO4J_PASSWORD", "")
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

    # Generator identity (v4, session-scoped — no TOML key)
    generator_id: str | None = field(
        default_factory=lambda: os.environ.get("MEMORY_GENERATOR")
    )

    # Schema
    schema_version: int = SCHEMA_VERSION
    valid_types: tuple = tuple(sorted(VALID_TYPES))
    valid_relation_types: tuple = tuple(sorted(ALL_RELATION_TYPES))

    # L0 budget
    l0_token_budget: int = 2000

    # Retrieval
    recency_decay: float = 0.995
    association_k: int = 10
    recall_depth: int = 2
    recall_decay: float = 0.8
    max_inherit_depth: int = 3  # max hierarchy levels for scope matching
    verification_staleness_days: int = 7  # staleness threshold for verified_at display
    mitigation_dampening: float = 0.95  # score multiplier for entries with inbound MITIGATES

    # Gate probes (v4)
    numeric_probe_enabled: bool = True
    numeric_probe_mode: str = 'log'  # 'log' (default burn-in) or 'quarantine'
    numeric_probe_sim_threshold: float = 0.80
    l0_echo_threshold: float = 0.6

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
        1. CLI flags (explicit user intent)
        2. Environment variables (ambient deployment config)
        3. Parent memoryschema.toml (wins over child on conflict)
        4. Child memoryschema.toml
        5. Dataclass defaults
        """
        from memoryschema.inheritance import resolve_config_chain, validate_toml_name
        resolved = resolve_config_chain(Path(project_root).resolve())
        # Convert store_path to Path if present as string
        if 'store_path' in resolved and isinstance(resolved['store_path'], str):
            resolved['store_path'] = Path(project_root) / resolved['store_path']
        instance = cls(**{k: v for k, v in resolved.items()
                         if k in cls.__dataclass_fields__})

        # Layer 2: Env vars override TOML (but not CLI)
        _ENV_OVERRIDES = {
            'NEO4J_URI': 'neo4j_uri',
            'NEO4J_USER': 'neo4j_user',
            'NEO4J_PASSWORD': 'neo4j_password',
            'VOYAGE_API_KEY': 'voyage_api_key',
            'MEMORY_PROJECT': 'project_name',
        }
        for env_var, field_name in _ENV_OVERRIDES.items():
            val = os.environ.get(env_var)
            if val is not None:
                setattr(instance, field_name, val)

        # Layer 1: CLI overrides beat everything (applied last = highest priority)
        if cli_overrides:
            for field_name, val in cli_overrides.items():
                if val is not None and field_name in cls.__dataclass_fields__:
                    setattr(instance, field_name, val)

        instance._name_warning = validate_toml_name(Path(project_root).resolve())
        return instance

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
