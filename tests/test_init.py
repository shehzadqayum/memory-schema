"""Tests for __init__.py — public API exports and lazy imports."""

import pytest


class TestDirectImports:
    """Test that direct imports work without optional deps."""

    def test_import_memoryschema(self):
        import memoryschema
        assert hasattr(memoryschema, '__version__')

    def test_version_is_string(self):
        from memoryschema import __version__
        assert isinstance(__version__, str)
        assert '.' in __version__

    def test_import_memory_config(self):
        from memoryschema import MemoryConfig
        config = MemoryConfig()
        assert config.project_name == "default"

    def test_import_memory_store(self):
        from memoryschema import MemoryStore
        assert MemoryStore is not None

    def test_import_get_store(self):
        from memoryschema import get_store
        assert callable(get_store)

    def test_import_parse_memory_file(self):
        from memoryschema import parse_memory_file
        assert callable(parse_memory_file)

    def test_import_parse_memory_content(self):
        from memoryschema import parse_memory_content
        assert callable(parse_memory_content)

    def test_import_discover_memory_files(self):
        from memoryschema import discover_memory_files
        assert callable(discover_memory_files)

    def test_import_validate(self):
        from memoryschema import validate
        assert callable(validate)

    def test_import_validate_file(self):
        from memoryschema import validate_file
        assert callable(validate_file)

    def test_import_validate_directory(self):
        from memoryschema import validate_directory
        assert callable(validate_directory)

    def test_import_extract_entity_block(self):
        from memoryschema import extract_entity_block
        assert callable(extract_entity_block)

    def test_import_parse_entity(self):
        from memoryschema import parse_entity
        assert callable(parse_entity)

    def test_import_consolidate(self):
        from memoryschema import consolidate
        assert callable(consolidate)


class TestLazyImports:
    """Test __getattr__ lazy loading for optional deps."""

    def test_neo4j_memory_store(self):
        from memoryschema import Neo4jMemoryStore
        assert Neo4jMemoryStore.__name__ == 'Neo4jMemoryStore'

    def test_embed_text(self):
        from memoryschema import embed_text
        assert callable(embed_text)

    def test_embed_batch(self):
        from memoryschema import embed_batch
        assert callable(embed_batch)

    def test_rerank(self):
        from memoryschema import rerank
        assert callable(rerank)

    def test_unknown_attr_raises(self):
        import memoryschema
        with pytest.raises(AttributeError, match="no attribute"):
            _ = memoryschema.nonexistent_thing


class TestAllExports:
    """Test that __all__ is complete and consistent."""

    def test_all_defined(self):
        import memoryschema
        assert hasattr(memoryschema, '__all__')
        assert isinstance(memoryschema.__all__, list)

    def test_all_importable(self):
        import memoryschema
        for name in memoryschema.__all__:
            obj = getattr(memoryschema, name)
            assert obj is not None, f"__all__ entry '{name}' is None"

    def test_all_contains_core(self):
        import memoryschema
        core = [
            'MemoryConfig', 'MemoryStore', 'get_store',
            'parse_memory_file', 'parse_memory_content',
            'discover_memory_files', 'validate', 'consolidate',
        ]
        for name in core:
            assert name in memoryschema.__all__, f"'{name}' missing from __all__"

    def test_all_contains_lazy(self):
        import memoryschema
        lazy = ['Neo4jMemoryStore', 'embed_text', 'embed_batch', 'rerank']
        for name in lazy:
            assert name in memoryschema.__all__, f"lazy '{name}' missing from __all__"
