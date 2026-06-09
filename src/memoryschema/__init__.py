"""
memoryschema — XML-based memory entity system.

Install:
    pip install memory-schema[all]

Public API:
    MemoryConfig          Configuration dataclass
    MemoryStore           JSONL-backed memory store (L1b)
    get_store             Factory: best available backend

    parse_memory_file     Parse a .md memory file into dict
    parse_memory_content  Parse raw content string into dict
    discover_memory_files Find all .md files under a path

    validate              Validate memory content against schema
    validate_file         Validate a file
    validate_directory    Validate all files in a directory

    consolidate           Batch index un-indexed files

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
from memoryschema.consolidation import consolidate

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
    raise AttributeError(f"module 'memoryschema' has no attribute {name}")
