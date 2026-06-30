"""
Neo4j schema setup.

Creates indexes, constraints, and full-text search for the memory graph.
Requires: pip install memory-schema[neo4j]

Usage:
    from memoryschema.schema import setup_schema
    setup_schema(config)
"""


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

        # Declarative vector-index DDL (Neo4j 5.11+) — idempotent via IF NOT EXISTS, unlike the
        # legacy db.index.vector.createNodeIndex(...) which throws EquivalentSchemaRuleAlreadyExists
        # on re-run and broke `neo4j reset`/`schema`/`deploy`. Backticks on the dotted option keys
        # are required. (helios local patch — re-apply on re-vendor.)
        session.run("""
            CREATE VECTOR INDEX memory_embedding IF NOT EXISTS
            FOR (m:Memory) ON (m.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 1024,
                `vector.similarity_function`: 'cosine'
            }}
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
    from memoryschema.neo4j_store import connect
    driver = connect(config=config)      # shared driver build + RETURN 1 probe + friendly auth error
    try:
        create_schema(driver)
        return verify_schema(driver)
    finally:
        driver.close()
