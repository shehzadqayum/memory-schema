"""v0.1.2 regression: the PostToolUse hook must survive UTF-8 store/entity content on Windows.

The hook's inline Python scanned store.jsonl with the platform-default codec — on Windows that is
cp1252, and a store containing bytes like 0x8f (e.g. 'Ə' U+018F) crashed EVERY memory-file index
(UnicodeDecodeError, observed live in a consumer 2026-07-14). The fix is belt (export PYTHONUTF8=1
inside the script — the hook env must be self-sufficient) and suspenders (encoding='utf-8' on the
inline opens). The behavioral test drives the REAL hook + REAL interpreter against a store seeded
with the offending byte and an env stripped of UTF-8 vars; the static test pins the script contract.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "src" / "memoryschema" / "hooks" / "hook-post-write.sh"
SRC = pathlib.Path(__file__).resolve().parent.parent / "src"


def _fwd(p):
    return str(p).replace("\\", "/")


def test_hook_indexes_past_utf8_store_without_ambient_utf8_env(tmp_path):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash required on PATH")

    (tmp_path / "memory").mkdir()
    # a pre-existing store row whose UTF-8 bytes include 0x8f — undefined in cp1252, so a
    # codec-default lazy read crashes mid-iteration exactly like the live failure
    (tmp_path / "memory" / "store.jsonl").write_text(
        json.dumps({"name": "seed", "schema": 5,
                    "description": "Ə em—dash → arrows ✓"}) + "\n",
        encoding="utf-8")
    memfile = tmp_path / "memory" / "utf8-probe.md"
    memfile.write_text("---\nschema: 5\n---\n\nUtf8 probe entity.\n\n## Observations\n- o\n",
                       encoding="utf-8")

    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}      # the hook must self-provide UTF-8
    env["NEO4J_URI"] = "bolt://127.0.0.1:59999"                  # dead endpoint → JSONL fallback
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")

    payload = '{"tool_name":"Write","tool_input":{"file_path":"' + _fwd(memfile) + '"}}'
    r = subprocess.run([bash, _fwd(HOOK), _fwd(sys.executable)], input=payload, text=True,
                       capture_output=True, timeout=120, env=env)
    assert "UnicodeDecodeError" not in (r.stderr or ""), r.stderr
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"
    rows = [json.loads(l) for l in
            (tmp_path / "memory" / "store.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert any(row.get("name") == "utf8-probe" for row in rows), "entity was not indexed"


def test_hook_script_pins_utf8_contract():
    text = HOOK.read_text(encoding="utf-8")
    assert "export PYTHONUTF8=1" in text
    assert "export PYTHONIOENCODING=utf-8" in text
    offenders = [ln.strip() for ln in text.splitlines()
                 if "open(" in ln and "encoding=" not in ln and not ln.strip().startswith("#")]
    assert not offenders, f"open() without encoding= in the hook: {offenders}"
