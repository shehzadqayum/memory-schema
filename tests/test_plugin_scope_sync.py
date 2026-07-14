"""v0.2.0: plugin sync is scope-aware — a scope-gated rule a project never opted into is not drift.

Before this, sync --check compared every deployment against the FULL packaged set, so a fresh
working-scope project phantom-drifted on the corpus rule forever (fractal bootstrap feedback), and
a plain sync force-deployed rules the project never chose. Opt-in is inferred from presence
(deployed at init --scopes or via sync --scopes) — stateless and self-describing.
"""
import json

from click.testing import CliRunner

from memoryschema.cli.main import cli

ENV = {"MEMORYSCHEMA_SKIP_PREFLIGHT": "1"}
CORPUS = "rules-ondemand/memory-corpus.md"


def _sync(tmp_path, *args):
    return CliRunner().invoke(
        cli, ["--root", str(tmp_path), "plugin", "sync", "--json", *args], env=ENV)


def _files(result):
    out = result.output
    payload = out[out.index("["):out.rindex("]") + 1]     # trailing summary lines follow the JSON
    return {r["file"]: r["status"] for r in json.loads(payload)}


def test_fresh_working_scope_project_has_no_corpus_phantom(tmp_path):
    (tmp_path / "memory").mkdir()
    r = _sync(tmp_path)                       # first deploy: base artefacts only
    assert r.exit_code == 0, r.output
    assert CORPUS not in _files(r), "an un-opted scope rule must not be deployed"
    chk = _sync(tmp_path, "--check")          # the fractal phantom-drift repro
    assert chk.exit_code == 0, chk.output
    assert CORPUS not in _files(chk)


def test_scopes_flag_opts_in_and_presence_is_sticky(tmp_path):
    (tmp_path / "memory").mkdir()
    r = _sync(tmp_path, "--scopes", "corpus")
    assert r.exit_code == 0, r.output
    assert _files(r).get(CORPUS) in ("written", "in-sync")
    corpus_path = tmp_path / ".claude" / CORPUS
    assert corpus_path.exists()

    chk = _sync(tmp_path, "--check")          # no flag needed — presence infers the opt-in
    assert chk.exit_code == 0, chk.output
    assert _files(chk).get(CORPUS) == "in-sync"

    corpus_path.write_text("locally edited\n", encoding="utf-8")
    chk2 = _sync(tmp_path, "--check")
    assert chk2.exit_code == 1, "drift on an opted-in scope rule must still fail --check"
    assert _files(chk2).get(CORPUS) == "drift"
