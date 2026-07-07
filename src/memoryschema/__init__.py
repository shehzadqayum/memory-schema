"""
memoryschema — file-first memory entity system (schema v5; legacy v4 XML parses).

Install:
    pip install memory-schema[all]

Public API:
    MemoryConfig          Configuration dataclass
    MemoryStore           JSONL-backed memory store (L1b)
    get_store             Factory: best available backend

    parse_memory_file     Parse a .md memory file into dict
    parse_memory_content  Parse raw content string into dict
    discover_memory_files Find all .md files under a path

    validate              Validate v4 memory content against schema (V1-V12, R1-R6)
    validate_file         Validate a file
    validate_directory    Validate all files in a directory

    consolidate           Batch index un-indexed files
    reflect               Cluster episodic entries → semantic summaries

    Hierarchy: parse_project_path, parent_project, ancestor_projects,
               is_ancestor_of, is_descendant_of, project_matches_scope,
               project_matches_filter, validate_project_name
    Inheritance: resolve_config_chain, resolve_rules

Optional (require extras):
    Neo4jMemoryStore      Neo4j-backed store (requires: pip install memory-schema[neo4j])
    embed_text            Embed single text (requires: pip install memory-schema[embeddings])
    embed_batch           Embed multiple texts (requires: pip install memory-schema[embeddings])
    rerank                Rerank documents (requires: pip install memory-schema[embeddings])
"""

from memoryschema._version import __version__
from memoryschema.config import MemoryConfig
from memoryschema.store import MemoryStore, get_store
from memoryschema.tags import parse_memory_file, parse_memory_content
from memoryschema.discovery import discover_memory_files
from memoryschema.validator import (
    validate,
    validate_file,
    validate_directory,
    extract_entity_block,
    parse_entity,
)
from memoryschema.consolidation import consolidate, reflect
from memoryschema.inheritance import resolve_config_chain, resolve_rules
from memoryschema.hierarchy import (
    parse_project_path,
    parent_project,
    ancestor_projects,
    is_ancestor_of,
    is_descendant_of,
    project_matches_scope,
    project_matches_filter,
    validate_project_name,
)

__all__ = [
    "__version__",
    "MemoryConfig",
    "MemoryStore",
    "get_store",
    "parse_memory_file",
    "parse_memory_content",
    "discover_memory_files",
    "validate",
    "validate_file",
    "validate_directory",
    "extract_entity_block",
    "parse_entity",
    "consolidate",
    "reflect",
    # Hierarchy
    "parse_project_path",
    "parent_project",
    "ancestor_projects",
    "is_ancestor_of",
    "is_descendant_of",
    "project_matches_scope",
    "project_matches_filter",
    "validate_project_name",
    # Inheritance
    "resolve_config_chain",
    "resolve_rules",
    # Lazy imports (optional deps)
    "Neo4jMemoryStore",
    "embed_text",
    "embed_batch",
    "rerank",
]


def __getattr__(name):
    """Lazy imports for optional dependencies.

    Neo4jMemoryStore requires: pip install memory-schema[neo4j]
    embed_text/embed_batch/rerank require: pip install memory-schema[embeddings]
    """
    if name == "Neo4jMemoryStore":
        from memoryschema.neo4j_store import Neo4jMemoryStore
        return Neo4jMemoryStore
    if name in ("embed_text", "embed_batch", "rerank"):
        import memoryschema.embeddings as _emb
        return getattr(_emb, name)
    if name == "embeddings":
        # PEP 562 lazy submodule: lets mock.patch("memoryschema.embeddings.x")
        # resolve regardless of import order (resolve_name uses getattr chains,
        # which otherwise only work if the submodule happens to be imported).
        import memoryschema.embeddings as _emb
        return _emb
    raise AttributeError(f"module 'memoryschema' has no attribute {name}")
