"""A JSONL merge carrying new vectors must actually rewrite the sidecar `.npz` (not keep stale vectors).

Regression for the merge-whitelist bug: `embed_input_hash` was NOT in the merge whitelist, so a merge that
carried new `embedding`/`embeddings` kept the OLD stored hash — and `externalize()`'s skip-if-unchanged then
skipped the rewrite, dropping the new vectors. Recall would score new text against the old embedding until
`reconcile`. Adding the hash to the whitelist fixes it end-to-end.
"""
import glob
import os

import numpy as np

from memoryschema.store import MemoryStore
from memoryschema.vector_sidecar import sidecar_dir


def test_merge_with_new_vectors_rewrites_the_sidecar(tmp_path):
    p = str(tmp_path / "store.jsonl")
    s = MemoryStore(p)
    s.upsert({"name": "e", "schema": 5, "description": "old text",
              "embedding": [0.1, 0.1, 0.1, 0.1], "embed_input_hash": "h1"})
    # MERGE (same name, existing entity): new content + new vectors + new provenance hash
    s.upsert({"name": "e", "schema": 5, "description": "new text",
              "embedding": [0.9, 0.9, 0.9, 0.9], "embed_input_hash": "h2"})

    npzs = glob.glob(os.path.join(sidecar_dir(p), "*.npz"))
    assert npzs, "the sidecar .npz must exist"
    with np.load(npzs[0]) as z:
        assert str(z["hash"]) == "h2", "the sidecar must rewrite on a merge carrying a new provenance hash"
        assert list(np.asarray(z["embedding"])) == [0.9, 0.9, 0.9, 0.9], "the NEW vectors must be persisted"
