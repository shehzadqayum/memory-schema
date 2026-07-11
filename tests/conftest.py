"""Shared pytest fixtures + suite-wide isolation from any live backend.

HERMETIC ISOLATION (helios local patch — re-apply on package re-vendor):
The CLI tests (index/import/embed/…) correctly isolate their *files* via ``--root <tmp>``, but the
Neo4j and Voyage backends are driven by the *environment* (NEO4J_URI/USER/PASSWORD, VOYAGE_API_KEY),
not by ``--root``. So when the suite is run in a shell that has the live ``.env`` loaded — which is the
normal Helios working state, and exactly how ``memoryschema doctor`` spawns pytest — those tests write
fixture entities (``test``, ``imported``) into whatever Neo4j the env points at: the **live**
``trading-journal`` container. Likewise a real ``VOYAGE_API_KEY`` triggers real embedding calls.

This autouse fixture strips those backend vars (plus ``MEMORY_ROOT``/``MEMORY_PROJECT``, which otherwise
leak the ambient project into config-resolution tests) for every **non-integration** test, forcing the
root-isolated JSONL store. Integration tests (``@pytest.mark.integration``, excluded by default via
``addopts = -m 'not integration'``) opt in and keep their real credentials.

Net effect: ``pytest`` / ``doctor`` can be run with the live ``.env`` loaded without ever touching the
live memory store. The suite behaves exactly as it does in a pristine shell.
"""

import pytest

# A guaranteed-dead bolt endpoint: a non-integration test that builds a default-config store must
# connect HERE (fast connection-refused -> JSONL fallback), never the developer's live localhost:7687.
DEAD_NEO4J_URI = "bolt://127.0.0.1:59999"

# Env vars that, if present, route a test at a *live* backend or leak ambient project config.
_LIVE_BACKEND_ENV = (
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "VOYAGE_API_KEY",
    "MEMORY_ROOT",
    "MEMORY_PROJECT",
    # helios default-mode flags: their factory default is ON, so they must be stripped AND
    # forced off below, or non-integration tests would hard-require a (hermetically absent) Neo4j.
    "MEMORYSCHEMA_REQUIRE_NEO4J",
    "MEMORYSCHEMA_REQUIRE_VOYAGE",
    # v5 is now the authored default (schema-split B2). Strip both format flags so tests run against the
    # real default; the few v4-specific tests (v4 injection/escaping) opt INTO v4 via monkeypatch.setenv.
    # (The deployment .env may set MEMORYSCHEMA_V5=1 — now redundant with the default, but strip it anyway
    # so a leaked MEMORYSCHEMA_V4 can never silently flip a test to the legacy branch.)
    "MEMORYSCHEMA_V5",
    "MEMORYSCHEMA_V4",
)


@pytest.fixture(autouse=True)
def _isolate_from_live_backend(request, monkeypatch):
    """Strip live-backend / ambient-project env vars for non-integration tests.

    monkeypatch restores the original environment after each test, so this never affects the
    surrounding shell or subsequent integration runs.
    """
    if "integration" in request.keywords:
        return
    for var in _LIVE_BACKEND_ENV:
        monkeypatch.delenv(var, raising=False)
    # Stripping NEO4J_URI alone is NOT enough: MemoryConfig's default-factory then resolves to the
    # live localhost:7687, so the suite would connect to (and stall on) a running container. Point it
    # at a guaranteed-dead endpoint so get_store always fails fast to JSONL regardless of host state.
    monkeypatch.setenv("NEO4J_URI", DEAD_NEO4J_URI)
    # Force the default-mode dependency gates OFF for hermetic unit tests: don't hard-require
    # the absent Neo4j, and don't run the CLI preflight (which would shell out to docker).
    monkeypatch.setenv("MEMORYSCHEMA_REQUIRE_NEO4J", "false")
    monkeypatch.setenv("MEMORYSCHEMA_SKIP_PREFLIGHT", "1")
    monkeypatch.setenv("MEMORYSCHEMA_RECALL_LOG", "0")   # don't write recall telemetry during tests


@pytest.fixture(autouse=True, scope="session")
def _live_neo4j_wipe_tripwire():
    """Snapshot the LIVE Neo4j Memory-node count at session start; scream at session end
    if it dropped. On 2026-07-04 a failure-cascade suite run (numpy eviction via
    patch.dict(sys.modules) breaking isolation) wiped the live store to 0 nodes with no
    test identifying itself. The .md/JSONL layers made it recoverable (reconcile), but a
    silent wipe must never be silent again. Runs at session scope, BEFORE the per-test
    env strip, so it sees the real environment when the developer shell has .env loaded."""
    import os
    import sys
    uri = os.environ.get("NEO4J_URI")
    pwd = os.environ.get("NEO4J_PASSWORD")

    def _count():
        from neo4j import GraphDatabase
        d = GraphDatabase.driver(uri, auth=(os.environ.get("NEO4J_USER", "neo4j"), pwd))
        try:
            with d.session() as sess:
                return sess.run("MATCH (m:Memory) RETURN count(m) AS c").single()["c"]
        finally:
            d.close()

    before = None
    if uri and pwd and DEAD_NEO4J_URI not in uri:
        try:
            before = _count()
        except Exception:
            before = None
    yield
    if before:
        try:
            after = _count()
        except Exception:
            return
        if after < before:
            banner = "*" * 78
            msg = (
                banner
                + chr(10) + "*** LIVE NEO4J TRIPWIRE: Memory nodes %d -> %d during this" % (before, after)
                + chr(10) + "*** test session - a test touched the LIVE store. Restore with"
                + chr(10) + "*** 'memoryschema reconcile' and hunt the leaking test before"
                + chr(10) + "*** trusting the suite again."
                + chr(10) + banner
            )
            print(chr(10) + msg, file=sys.stderr)


@pytest.fixture
def dead_neo4j():
    """A MemoryConfig pointed at the guaranteed-dead bolt endpoint — for tests that need an explicit
    'Neo4j is down' config without hardcoding the port. Pairs with the autouse isolation above."""
    from memoryschema.config import MemoryConfig
    return lambda **kw: MemoryConfig(neo4j_uri=DEAD_NEO4J_URI, neo4j_password="x", **kw)
