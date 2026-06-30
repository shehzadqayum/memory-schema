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


@pytest.fixture
def dead_neo4j():
    """A MemoryConfig pointed at the guaranteed-dead bolt endpoint — for tests that need an explicit
    'Neo4j is down' config without hardcoding the port. Pairs with the autouse isolation above."""
    from memoryschema.config import MemoryConfig
    return lambda **kw: MemoryConfig(neo4j_uri=DEAD_NEO4J_URI, neo4j_password="x", **kw)
