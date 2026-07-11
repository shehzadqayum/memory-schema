"""P0 regression: the Neo4j vector index must be created idempotently.

The old code used the legacy `CALL db.index.vector.createNodeIndex(...)` which has no
IF NOT EXISTS and threw EquivalentSchemaRuleAlreadyExistsException on the 2nd run, breaking
`neo4j reset`/`schema`/`deploy`.
"""
from unittest.mock import MagicMock

import pytest

from memoryschema.schema import create_schema


def _capturing_driver(statements):
    drv = MagicMock()
    sess = MagicMock()
    drv.session.return_value.__enter__ = MagicMock(return_value=sess)
    drv.session.return_value.__exit__ = MagicMock(return_value=False)
    sess.run.side_effect = lambda q, **kw: statements.append(q)
    return drv


def test_vector_index_is_declarative_and_guarded():
    stmts = []
    create_schema(_capturing_driver(stmts))
    joined = "\n".join(stmts)
    assert "CREATE VECTOR INDEX memory_embedding IF NOT EXISTS" in joined
    assert "db.index.vector.createNodeIndex" not in joined          # legacy procedure gone
    # every index/constraint create is guarded with IF NOT EXISTS
    creates = [s for s in stmts if "CREATE" in s.upper() and ("INDEX" in s.upper() or "CONSTRAINT" in s.upper())]
    assert creates
    assert all("IF NOT EXISTS" in s.upper() for s in creates)


def test_create_schema_idempotent_against_already_exists():
    """A FakeSession that raises (like Neo4j) for an UNGUARDED create run twice. With every
    create guarded by IF NOT EXISTS, create_schema can run repeatedly without error."""
    class EquivalentSchemaRuleAlreadyExists(Exception):
        pass

    seen = set()

    class Sess:
        def run(self, q, **kw):
            up = q.upper()
            unguarded = ("CREATENODEINDEX" in up) or (
                ("CREATE INDEX" in up or "CREATE VECTOR INDEX" in up
                 or "CREATE CONSTRAINT" in up or "CREATE FULLTEXT" in up)
                and "IF NOT EXISTS" not in up)
            if unguarded:
                key = q.strip()
                if key in seen:
                    raise EquivalentSchemaRuleAlreadyExists("An equivalent index already exists")
                seen.add(key)
            return MagicMock()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    drv = MagicMock()
    drv.session.return_value = Sess()
    create_schema(drv)
    create_schema(drv)   # must NOT raise (the regression would raise here)
