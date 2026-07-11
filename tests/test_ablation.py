"""Move 2/3: the multi-space ablation runner + the backend-benchmark CLI mode.

Hermetic: run_ablation is pure (mocked embed_fn, tiny in-memory entries); the backend CLI smoke uses
a dead Neo4j (-> UNAVAILABLE) + a tmp JSONL store.
"""
from click.testing import CliRunner

from memoryschema.eval.ablation import run_ablation


def _entries():
    # 3 entities; 'alpha' is the intended target. 2-D vectors keep cosine trivial to reason about.
    return [
        {"name": "alpha", "embedding": [1.0, 0.0],
         "embeddings": {"default": [1.0, 0.0], "observations": [1.0, 0.0]},
         "divergence_profile": {"observations": 0.1}},
        {"name": "beta", "embedding": [0.0, 1.0], "embeddings": {"default": [0.0, 1.0]}},
        {"name": "gamma", "embedding": [0.7, 0.7], "embeddings": {"default": [0.7, 0.7]}},
    ]


def _gold():
    return [{"query": "q", "relevant": ["alpha"], "description": "t"}]


def test_run_ablation_shape_and_ranking():
    r = run_ablation(_entries(), _gold(), embed_fn=lambda t: [1.0, 0.0])   # query ~ alpha
    assert r["n_queries"] == 1 and r["n_entities"] == 3
    for sect in ("single", "multi", "delta"):
        assert set(r[sect]) == {"recall@5", "recall@10", "mrr", "ndcg@10"}
    assert isinstance(r["keep_multispace"], bool)
    assert r["single"]["mrr"] == 1.0          # alpha is the top single-space hit


def test_single_equals_multi_when_default_only():
    # With only the default space, combine_similarities(len==1) returns it -> single == multi.
    entries = [{"name": "alpha", "embedding": [1.0, 0.0], "embeddings": {"default": [1.0, 0.0]}},
               {"name": "beta", "embedding": [0.0, 1.0], "embeddings": {"default": [0.0, 1.0]}}]
    r = run_ablation(entries, _gold(), embed_fn=lambda t: [1.0, 0.0])
    assert r["delta"]["mrr"] == 0.0 and r["delta"]["recall@5"] == 0.0
    assert r["keep_multispace"] is False      # no lift -> dormant


def test_skips_empty_gold_and_failed_embedding():
    r = run_ablation(_entries(), [{"query": "q", "relevant": [], "description": "x"}],
                     embed_fn=lambda t: [1.0, 0.0])
    assert r["n_queries"] == 0                 # empty-relevant query skipped
    r2 = run_ablation(_entries(), _gold(), embed_fn=lambda t: None)
    assert r2["n_queries"] == 0                # embedding failure skipped, no crash


def test_eval_backends_cli_neo4j_unavailable(tmp_path, dead_neo4j):
    """eval --mode backends: a dead Neo4j is reported UNAVAILABLE; the JSONL path still runs (exit 0)."""
    from memoryschema.cli.eval_cmd import eval_cmd
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    cfg = dead_neo4j(project_root=str(tmp_path))
    r = CliRunner().invoke(eval_cmd, ["--mode", "backends"], obj=cfg)
    assert r.exit_code == 0
    assert "UNAVAILABLE" in r.output and "jsonl" in r.output
