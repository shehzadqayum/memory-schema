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

# Env vars that, if present, route a test at a *live* backend or leak ambient project config.
_LIVE_BACKEND_ENV = (
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "VOYAGE_API_KEY",
    "MEMORY_ROOT",
    "MEMORY_PROJECT",
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
