"""
Neo4j schema setup.

Creates indexes, constraints, and full-text search for the memory graph.
Requires: pip install memory-schema[neo4j]

Usage:
    from memoryschema.schema import setup_schema
    setup_schema(config)
"""

from neo4j import GraphDatabase


def create_schema(driver):
    """Create all indexes and constraints.

    Idempotent — safe to run multiple times. Creates:
    - Unique constraint on Memory.name
    - Vector index on Memory.embedding (1024 dims, cosine HNSW)
    - Full-text index on name, description, observations_text, prompt, reasoning
    - Range indexes on type, project, importance, last_accessed
    """
    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT memory_name_unique IF NOT EXISTS
            FOR (m:Memory) REQUIRE m.name IS UNIQUE
        """)

        session.run("""
            CALL db.index.vector.createNodeIndex(
                'memory_embedding',
                'Memory',
                'embedding',
                1024,
                'cosine'
            )
        """)

        session.run("""
            CREATE FULLTEXT INDEX memory_fulltext IF NOT EXISTS
            FOR (m:Memory)
            ON EACH [m.name, m.description, m.observations_text, m.prompt, m.reasoning]
        """)

        for field in ['type', 'project', 'importance', 'last_accessed']:
            session.run(f"""
                CREATE INDEX memory_{field} IF NOT EXISTS
                FOR (m:Memory) ON (m.{field})
            """)


def verify_schema(driver):
    """Verify all indexes exist. Returns list of index info dicts."""
    with driver.session() as session:
        result = session.run("SHOW INDEXES")
        return [dict(r) for r in result]


def setup_schema(config=None):
    """Convenience: create driver from config and run create_schema.

    Args:
        config: Optional MemoryConfig instance. Uses defaults if None.
    """
    if config is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()

    driver = GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
    )
    try:
        create_schema(driver)
        return verify_schema(driver)
    finally:
        driver.close()
