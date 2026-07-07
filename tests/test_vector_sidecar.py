"""Tests for the vector sidecar: externalize-on-save / rehydrate-on-load."""

import json
import os

import pytest

from memoryschema.store import MemoryStore
from memoryschema.vector_sidecar import (
    externalize,
    prune_orphans,
    rehydrate,
    sidecar_dir,
)

numpy = pytest.importorskip("numpy")


def _entry(name="vec-entry", h="hash-1"):
    return {
        "name": name,
        "description": "d",
        "observations": ["o1"],
        "embedding": [0.1, 0.2, 0.3],
        "embeddings": {"default": [0.1, 0.2, 0.3], "description": [0.4, 0.5, 0.6]},
        "divergence_profile": {"description": 0.12},
        "embed_input_hash": h,
    }


class TestExternalizeRehydrate:
    def test_roundtrip(self, tmp_path):
        sdir = str(tmp_path / ".embeddings")
        slim = externalize(_entry(), sdir)
        assert slim.get("vectors_external") is True
        assert "embedding" not in slim and "embeddings" not in slim
        assert slim["divergence_profile"] == {"description": 0.12}  # stays inline (tiny)
        assert os.path.exists(os.path.join(sdir, "vec-entry.npz"))

        back = rehydrate(dict(slim), sdir)
        assert back["embedding"] == pytest.approx([0.1, 0.2, 0.3], abs=1e-6)
        assert back["embeddings"]["description"] == pytest.approx([0.4, 0.5, 0.6], abs=1e-6)
        assert "vectors_external" not in back

    def test_skip_rewrite_when_hash_unchanged(self, tmp_path):
        sdir = str(tmp_path / ".embeddings")
        externalize(_entry(h="same"), sdir)
        path = os.path.join(sdir, "vec-entry.npz")
        mtime = os.path.getmtime(path)
        os.utime(path, (mtime - 100, mtime - 100))
        stamped = os.path.getmtime(path)
        externalize(_entry(h="same"), sdir)          # unchanged hash -> no rewrite
        assert os.path.getmtime(path) == stamped
        externalize(_entry(h="different"), sdir)     # changed hash -> rewrite
        assert os.path.getmtime(path) != stamped

    def test_no_vectors_passthrough(self, tmp_path):
        sdir = str(tmp_path / ".embeddings")
        e = {"name": "no-vec", "description": "d"}
        assert externalize(e, sdir) is e
        assert not os.path.exists(os.path.join(sdir, "no-vec.npz"))

    def test_missing_sidecar_degrades_unembedded(self, tmp_path):
        """Missing sidecar -> no vectors this load, but the marker is KEPT so a
        later load (or reconcile) retries and the entry is never permanently
        detached from an intact .npz by a numpy-less/missing-file pass."""
        sdir = str(tmp_path / ".embeddings")
        e = {"name": "ghost", "vectors_external": True}
        out = rehydrate(e, sdir)
        assert "embedding" not in out       # degraded to unembedded for this load
        assert out["vectors_external"] is True   # link preserved for retry

    def test_marker_popped_only_on_success(self, tmp_path):
        import numpy as np
        sdir = str(tmp_path / ".embeddings")
        externalize({"name": "real", "embedding": [0.1] * 8,
                     "embed_input_hash": "h1"}, sdir)
        out = rehydrate({"name": "real", "vectors_external": True}, sdir)
        assert "vectors_external" not in out          # success pops the marker
        assert len(out["embedding"]) == 8

    def test_unsafe_name_stays_inline(self, tmp_path):
        """A name with a path separator / '..' must not escape the sidecar dir
        or crash the save — it keeps its vectors inline instead."""
        sdir = str(tmp_path / ".embeddings")
        for bad in ("../evil", "plans/x", "a:b"):
            e = {"name": bad, "embedding": [0.1] * 4, "embed_input_hash": "h"}
            out = externalize(e, sdir)
            assert out is e                      # unchanged, vectors kept inline
        # nothing was written outside the (possibly absent) sidecar dir
        assert not os.path.exists(os.path.join(tmp_path, "evil.npz"))

    def test_prune_orphans(self, tmp_path):
        sdir = str(tmp_path / ".embeddings")
        externalize(_entry("keep"), sdir)
        externalize(_entry("drop"), sdir)
        n = prune_orphans(sdir, ["keep"])
        assert n == 1
        assert os.path.exists(os.path.join(sdir, "keep.npz"))
        assert not os.path.exists(os.path.join(sdir, "drop.npz"))


class TestStoreIntegration:
    def test_save_slim_load_full(self, tmp_path):
        store_path = str(tmp_path / "memory" / "store.jsonl")
        st = MemoryStore(store_path)
        st.upsert(_entry("m-one"))

        # On disk: slim (no vector arrays), sidecar exists
        raw = open(store_path, encoding="utf-8").read()
        line = json.loads(raw.splitlines()[0])
        assert line.get("vectors_external") is True
        assert "embedding" not in line
        assert os.path.exists(os.path.join(sidecar_dir(store_path), "m-one.npz"))

        # Fresh store: loads with vectors rehydrated (consumers unchanged)
        st2 = MemoryStore(store_path)
        got = st2.get("m-one")
        assert got["embedding"] == pytest.approx([0.1, 0.2, 0.3], abs=1e-6)
        assert got["embeddings"]["default"] == pytest.approx([0.1, 0.2, 0.3], abs=1e-6)

    def test_shrink_on_live_shaped_data(self, tmp_path):
        """A 1024-dim 7-space entity: the JSONL line must stay small."""
        store_path = str(tmp_path / "memory" / "store.jsonl")
        st = MemoryStore(store_path)
        big = _entry("big")
        big["embedding"] = [0.123456] * 1024
        big["embeddings"] = {s: [0.123456] * 1024 for s in
                             ("default", "name", "description", "observations",
                              "prompt", "reasoning", "chain")}
        st.upsert(big)
        line_len = len(open(store_path, encoding="utf-8").read())
        assert line_len < 2000, "vectors must not be inline (was ~140KB before the sidecar)"
