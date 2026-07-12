"""P3/P4: the preflight dependency gate must be loud, never silent.

Mocks the dep probes so the suite stays hermetic (no Docker/Neo4j/Voyage). The key
guarantee under test: a hard-required dependency being DOWN yields ok=False (anti-silent),
while a soft dependency (Voyage when not required) degrades with a warning rather than
failing.
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


def test_container_autostart_failure_is_loud(monkeypatch):
    """Auto-start ran but bolt never came up: must FAIL loud (ok=False), not silently 'ok'."""
    monkeypatch.setattr(pf, "_docker_engine_up", lambda: True)
    monkeypatch.setattr(pf, "_container_running", lambda c: False)        # stopped
    monkeypatch.setattr(pf, "_start_container", lambda c: (True, ""))     # start "succeeds"...
    monkeypatch.setattr(pf, "_wait_bolt", lambda c, timeout=40: (False, "bolt never came up"))  # ...but bolt doesn't
    monkeypatch.setattr(pf, "_voyage_ok", lambda c: (True, "ok"))
    r = pf.ensure_backend(_cfg(), auto_start=True, require=["neo4j"])
    assert r["ok"] is False                                               # the anti-silent guarantee
    assert any(c["name"] == "neo4j_container" and not c["ok"] for c in r["failures"])
    assert "FAIL" in pf.format_report(r)


# ── HIGH-1: the compose trust gate on the always-on auto-recovery path ─────────────────────────────
def test_compose_trust_gate(tmp_path):
    managed = tmp_path / "managed.yml"
    managed.write_text("# memoryschema-managed\nservices:\n  neo4j: {}\n", encoding="utf-8")
    hostile = tmp_path / "hostile.yml"
    hostile.write_text("services:\n  evil:\n    image: attacker/x\n", encoding="utf-8")
    assert pf._compose_is_trusted(str(managed)) is True
    assert pf._compose_is_trusted(str(hostile)) is False
    assert pf._compose_is_trusted(str(tmp_path / "missing.yml")) is False


def test_start_container_refuses_untrusted_compose(tmp_path, monkeypatch):
    """When the named container is absent, _start_container must NOT `compose up` a sentinel-less CWD file."""
    cfg = MemoryConfig(project_root=str(tmp_path))
    (tmp_path / "docker-compose.yml").write_text("services:\n  evil:\n    image: attacker/x\n", encoding="utf-8")
    calls = []
    def fake_run(args, timeout=10):
        calls.append(args)
        if args[:2] == ["docker", "start"]:
            return 1, "", "No such container"     # container does not exist
        return 0, "", ""                           # a compose-up would 'succeed' if we ever reached it
    monkeypatch.setattr(pf, "_run", fake_run)
    ok, err = pf._start_container(cfg)
    assert ok is False and "not a memoryschema-managed" in err
    assert not any("compose" in a for a in calls), "must NOT run `compose up` on an untrusted file"


# ── the implicit gate's cheap .md-vs-JSONL drift banner (kill-safety: silent drift → loud) ─────────
def _drift_project(tmp_path, jsonl_body):
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "alpha.md").write_text("---\nschema: 5\n---\n\nAlpha entity.\n", encoding="utf-8")
    (mem / "store.jsonl").write_text(jsonl_body, encoding="utf-8")
    return MemoryConfig(project_root=str(tmp_path))


def test_maybe_preflight_emits_store_drift_banner(tmp_path, monkeypatch, capsys):
    """A healthy backend + a drifted store (one .md entity, empty JSONL) → the cheap drift banner MUST fire."""
    from memoryschema.cli.main import _maybe_preflight
    monkeypatch.setattr(pf, "ensure_backend", lambda cfg, **kw: {"ok": True, "degraded": False})
    monkeypatch.delenv("MEMORYSCHEMA_SKIP_PREFLIGHT", raising=False)
    _maybe_preflight(_drift_project(tmp_path, ""))                    # JSONL empty → alpha missing
    err = capsys.readouterr().err
    assert "store drift" in err and "reconcile" in err


def test_maybe_preflight_silent_when_in_sync(tmp_path, monkeypatch, capsys):
    """No drift → no banner (the gate must not cry wolf on a clean store)."""
    import json
    from memoryschema.cli.main import _maybe_preflight
    monkeypatch.setattr(pf, "ensure_backend", lambda cfg, **kw: {"ok": True, "degraded": False})
    monkeypatch.delenv("MEMORYSCHEMA_SKIP_PREFLIGHT", raising=False)
    cfg = _drift_project(tmp_path, json.dumps({"name": "alpha", "schema": 5}) + "\n")
    _maybe_preflight(cfg)
    assert "store drift" not in capsys.readouterr().err


def test_drift_check_is_independently_throttled_when_degraded(tmp_path, monkeypatch):
    """A degraded backend never writes .preflight_ok, so _maybe_preflight runs on every call; the drift check
    must be throttled by its OWN marker so it does not re-parse the whole corpus each invocation."""
    import memoryschema.reconcile as rc
    from memoryschema.cli.main import _maybe_preflight
    calls = {"n": 0}
    def counting_local_drift(cfg):
        calls["n"] += 1
        return {"md_count": 0, "jsonl_count": 0, "missing_from_jsonl": [], "jsonl_orphans": [], "malformed": []}
    monkeypatch.setattr(rc, "local_drift", counting_local_drift)
    # degraded: ok=False -> the .preflight_ok health marker is never written, so the body runs every call
    monkeypatch.setattr(pf, "ensure_backend", lambda cfg, **kw: {
        "ok": False, "degraded": False, "failures": [{"name": "neo4j", "detail": "down"}]})
    monkeypatch.delenv("MEMORYSCHEMA_SKIP_PREFLIGHT", raising=False)
    cfg = MemoryConfig(project_root=str(tmp_path))
    _maybe_preflight(cfg)      # runs the drift check, writes .drift_ok
    _maybe_preflight(cfg)      # .drift_ok fresh -> drift check throttled out
    assert calls["n"] == 1


def test_start_container_recovers_stopped_via_docker_start(tmp_path, monkeypatch):
    """A merely-stopped named container is recovered by `docker start` alone — no compose, no file executed."""
    cfg = MemoryConfig(project_root=str(tmp_path))
    calls = []
    def fake_run(args, timeout=10):
        calls.append(args)
        return (0, "", "") if args[:2] == ["docker", "start"] else (1, "", "should not reach")
    monkeypatch.setattr(pf, "_run", fake_run)
    ok, err = pf._start_container(cfg)
    assert ok is True
    assert calls == [["docker", "start", cfg.neo4j_container_name]], "should stop after docker start succeeds"
