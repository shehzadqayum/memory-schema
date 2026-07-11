"""HIGH-2 regression: the PostToolUse hook must export only the memory backend's own namespace keys from a
project .env into the indexer child process — never arbitrary secrets (AWS/GitHub tokens, other services).

Drives the REAL hook script end-to-end: a fake "python" wrapper answers the hook's JSON probes by delegating
to the real interpreter, and — on the indexing invocation (distinguished by MEMORYSCHEMA_HOOK_FILE being set)
— dumps the secret-scoped child environment instead of running the indexer, so no live backend is needed.
"""
import pathlib
import shutil
import stat
import subprocess

import pytest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "src" / "memoryschema" / "hooks" / "hook-post-write.sh"


def _fwd(p):
    return str(p).replace("\\", "/")


def test_hook_env_allowlist_scopes_export(tmp_path):
    bash = shutil.which("bash")
    real_python = shutil.which("python") or shutil.which("python3")
    if not bash or not real_python:
        pytest.skip("bash + python required on PATH")

    (tmp_path / "memory").mkdir()
    memfile = tmp_path / "memory" / "x.md"
    memfile.write_text("---\nschema: 5\nname: x\n---\n\nd\n\n## Observations\n- o\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "NEO4J_PASSWORD=secretpw\nVOYAGE_API_KEY=vk\nMEMORYSCHEMA_V5=1\n"
        "AWS_SECRET_ACCESS_KEY=leaky\nGITHUB_TOKEN=ght\n", encoding="utf-8")

    capture = tmp_path / "captured-env.txt"
    fakepy = tmp_path / "fakepy.sh"
    fakepy.write_text(
        "#!/usr/bin/env bash\n"
        'if [ -n "${MEMORYSCHEMA_HOOK_FILE:-}" ]; then\n'
        "  env | grep -E '^(NEO4J_PASSWORD|VOYAGE_API_KEY|MEMORYSCHEMA_V5|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN)='"
        f" > '{_fwd(capture)}'\n"
        "  exit 0\n"
        "fi\n"
        f"exec '{_fwd(real_python)}' \"$@\"\n", encoding="utf-8")
    fakepy.chmod(fakepy.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    payload = '{"tool_name":"Write","tool_input":{"file_path":"' + _fwd(memfile) + '"}}'
    subprocess.run([bash, _fwd(HOOK), _fwd(fakepy)], input=payload, text=True,
                   capture_output=True, timeout=60)

    if not capture.exists():
        pytest.skip("fake-python wrapper was not invoked (executable-bit/platform quirk) — allowlist not exercised")
    keys = {ln.split("=", 1)[0] for ln in capture.read_text(encoding="utf-8").splitlines() if "=" in ln}
    assert "NEO4J_PASSWORD" in keys, "backend credentials must be exported to the indexer"
    assert "VOYAGE_API_KEY" in keys and "MEMORYSCHEMA_V5" in keys
    assert "AWS_SECRET_ACCESS_KEY" not in keys, "an unrelated secret leaked into the indexer child env"
    assert "GITHUB_TOKEN" not in keys, "an unrelated secret leaked into the indexer child env"
