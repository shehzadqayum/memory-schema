"""P3/P4: the preflight dependency gate must be loud, never silent.

Mocks the dep probes so the suite stays hermetic (no Docker/Neo4j/Voyage). The key
guarantee under test: a hard-required dependency being DOWN yields ok=False (anti-silent),
while a soft dependency (Voyage when not required) degrades with a warning rather than
failing. (helios local patch test.)
"""
import memoryschema.preflight as pf
from memoryschema.config import MemoryConfig


def _cfg():
    return MemoryConfig(project_root=".")


def test_all_up_is_ok(monkeypatch):
    monkeypatch.setattr(pf, "_docker_engine_up", lambda: True)
    monkeypatch.setattr(pf, "_container_running", lambda c: True)
    monkeypatch.setattr(pf, "_bolt_and_schema", lambda c: (True, True, ""))
    monkeypatch.setattr(pf, "_voyage_ok", lambda c: (True, "1024 dims"))
    r = pf.ensure_backend(_cfg(), auto_start=False, require=["neo4j", "voyage"])
    assert r["ok"] is True
    assert r["degraded"] is False
    assert all(c["ok"] for c in r["checks"])


def test_neo4j_down_is_loud_not_silent(monkeypatch):
    monkeypatch.setattr(pf, "_docker_engine_up", lambda: False)   # engine down
    monkeypatch.setattr(pf, "_voyage_ok", lambda c: (True, "ok"))
    r = pf.ensure_backend(_cfg(), auto_start=False, require=["neo4j"])
    assert r["ok"] is False                                       # the anti-silent guarantee
    assert any(c["name"] == "docker_engine" and not c["ok"] for c in r["failures"])
    report = pf.format_report(r)
    assert "FAIL" in report


def test_voyage_down_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(pf, "_docker_engine_up", lambda: True)
    monkeypatch.setattr(pf, "_container_running", lambda c: True)
    monkeypatch.setattr(pf, "_bolt_and_schema", lambda c: (True, True, ""))
    monkeypatch.setattr(pf, "_voyage_ok", lambda c: (False, "VOYAGE_API_KEY not set"))
    r = pf.ensure_backend(_cfg(), auto_start=False, require=["neo4j"])   # voyage NOT required
    assert r["ok"] is True                                        # neo4j up -> overall ok
    assert r["degraded"] is True                                  # but degraded
    assert any(c["name"] == "voyage" for c in r["warnings"])


def test_container_autostart_attempted_when_stopped(monkeypatch):
    calls = {"start": 0}
    monkeypatch.setattr(pf, "_docker_engine_up", lambda: True)
    monkeypatch.setattr(pf, "_container_running", lambda c: False)   # stopped
    def _start(c):
        calls["start"] += 1
        return True, ""
    monkeypatch.setattr(pf, "_start_container", _start)
    monkeypatch.setattr(pf, "_wait_bolt", lambda c, timeout=40: (True, ""))
    monkeypatch.setattr(pf, "_bolt_and_schema", lambda c: (True, True, ""))
    monkeypatch.setattr(pf, "_voyage_ok", lambda c: (True, "ok"))
    r = pf.ensure_backend(_cfg(), auto_start=True, require=["neo4j"])
    assert calls["start"] == 1                                    # auto-recovery attempted
    assert r["ok"] is True
