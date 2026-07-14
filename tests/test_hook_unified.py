"""v0.2.0: the PostToolUse hook is a thin shim over write_index.index_memory — ONE pipeline.

The previous ~200-line inline duplicate drifted behind index_memory three separate times
(quarantine parity, config threading, the cp1252 store scan). These tests drive the REAL hook
script end-to-end and pin the exit-code contract, plus the IndexResult outcome flags the shim
maps from. One deliberate behavior change rides along: hook writes now DUAL-write, so
store.jsonl no longer lags Neo4j between reconciles.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from memoryschema.write_index import index_memory

HOOK = pathlib.Path(__file__).resolve().parent.parent / "src" / "memoryschema" / "hooks" / "hook-post-write.sh"
SRC = pathlib.Path(__file__).resolve().parent.parent / "src"

_MALFORMED_V4 = ('<memory:entity schema="4" name="bad">'
                 '<memory:description>raw & ampersand breaks the parse</memory:description>'
                 '</memory:entity>')


def _fwd(p):
    return str(p).replace("\\", "/")


def _run_hook(tmp_path, memfile):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash required on PATH")
    env = dict(os.environ)
    env["NEO4J_URI"] = "bolt://127.0.0.1:59999"          # dead endpoint — JSONL leg only
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    payload = '{"tool_name":"Write","tool_input":{"file_path":"' + _fwd(memfile) + '"}}'
    return subprocess.run([bash, _fwd(HOOK), _fwd(sys.executable)], input=payload, text=True,
                          capture_output=True, timeout=120, env=env)


def _rows(tmp_path):
    p = tmp_path / "memory" / "store.jsonl"
    if not p.exists():
        return {}
    return {json.loads(l)["name"]: json.loads(l)
            for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}


def test_new_entity_indexes_and_dual_write_reaches_jsonl(tmp_path):
    (tmp_path / "memory").mkdir()
    memfile = tmp_path / "memory" / "fresh-ent.md"
    memfile.write_text("---\nschema: 5\n---\n\nFresh entity.\n\n## Observations\n- o\n",
                       encoding="utf-8")
    r = _run_hook(tmp_path, memfile)
    assert r.returncode == 0, r.stderr
    # the unification's behavior improvement: the JSONL layer is written in the SAME hook call
    assert "fresh-ent" in _rows(tmp_path), "dual-write must land in store.jsonl immediately"
    assert (tmp_path / "memory" / "MEMORY.md").exists(), "L0 rebuild ran"


def test_existing_non_chain_entity_blocked_exit0(tmp_path):
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "store.jsonl").write_text(
        json.dumps({"name": "locked", "schema": 5, "description": "L"}) + "\n", encoding="utf-8")
    memfile = tmp_path / "memory" / "locked.md"
    memfile.write_text("---\nschema: 5\n---\n\nEdited content.\n", encoding="utf-8")
    r = _run_hook(tmp_path, memfile)
    assert r.returncode == 0, r.stderr                    # never blocks the Write tool
    assert "BLOCKED" in r.stderr and "read-only" in r.stderr
    assert _rows(tmp_path)["locked"].get("description") == "L", "blocked edit must not index"


def test_corrupted_entity_exits_2_with_guidance(tmp_path):
    (tmp_path / "memory").mkdir()
    memfile = tmp_path / "memory" / "bad.md"
    memfile.write_text(_MALFORMED_V4, encoding="utf-8")
    r = _run_hook(tmp_path, memfile)
    assert r.returncode == 2
    assert "CORRUPTED" in r.stderr and "NOT indexed" in r.stderr


def test_corrupted_v5_declared_is_loud_too(tmp_path):
    # v0.2.0 tightening: a DECLARED schema: 5 file that won't parse was silently skipped by the
    # old hook; reconcile's guard already treats it as malformed — the write path now agrees.
    (tmp_path / "memory").mkdir()
    memfile = tmp_path / "memory" / "badv5.md"
    memfile.write_text("---\nschema: 5\n", encoding="utf-8")     # unterminated fence
    r = _run_hook(tmp_path, memfile)
    assert r.returncode == 2
    assert "CORRUPTED" in r.stderr


def test_non_entity_md_exits_0_quietly(tmp_path):
    (tmp_path / "memory").mkdir()
    memfile = tmp_path / "memory" / "notes.md"
    memfile.write_text("# just notes\nno entity here\n", encoding="utf-8")
    r = _run_hook(tmp_path, memfile)
    assert r.returncode == 0, r.stderr
    assert "CORRUPTED" not in (r.stderr or "")


# ── IndexResult outcome flags (the contract the shim maps from) ──────────────────────────────
def test_index_memory_flags_corrupted_vs_skipped(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    bad = mem / "bad.md"
    bad.write_text(_MALFORMED_V4, encoding="utf-8")
    res = index_memory(str(bad))
    assert res.corrupted is True and res.skipped is False and res.ok is False

    notes = mem / "notes.md"
    notes.write_text("# notes\n", encoding="utf-8")
    res2 = index_memory(str(notes))
    assert res2.skipped is True and res2.corrupted is False


def test_index_memory_blocked_flag_and_generator_stamp(tmp_path, monkeypatch):
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "store.jsonl").write_text(
        json.dumps({"name": "locked", "schema": 5, "description": "L"}) + "\n", encoding="utf-8")
    f = mem / "locked.md"
    f.write_text("---\nschema: 5\n---\n\nEdit.\n", encoding="utf-8")
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:59999")
    res = index_memory(str(f))
    assert res.blocked is True and res.ok is False

    monkeypatch.setenv("MEMORY_GENERATOR", "test-gen")
    g = mem / "stamped.md"
    g.write_text("---\nschema: 5\n---\n\nStamped.\n", encoding="utf-8")
    res2 = index_memory(str(g))
    assert res2.ok, res2.errors
    rows = {json.loads(l)["name"]: json.loads(l)
            for l in (mem / "store.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    assert rows["stamped"].get("generator") == "test-gen"
