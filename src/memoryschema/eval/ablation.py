"""Multi-space ablation (value-measurement Move 2).

Compares SINGLE-space (default embedding only) vs MULTI-space (variance-weighted combiner) retrieval
on a labeled gold set, to decide whether the 7-space scoring earns its keep at the corpus's actual
size. Re-scores the same query/entity cosines two ways via spaces.combine_similarities — it never
re-embeds and never touches the store.

helios local patch — re-apply on re-vendor.
"""
from memoryschema.spaces import combine_similarities, _cos
from memoryschema.eval.metrics import recall_at_k, mrr, ndcg_at_k

# Pre-committed keep/drop threshold — set BEFORE seeing results to resist sunk-cost rationalization.
# Keep multi-space active only if it lifts mean MRR by at least this much over single-space.
MRR_LIFT_KEEP_THRESHOLD = 0.02

_KEYS = ("recall@5", "recall@10", "mrr", "ndcg@10")


def _entity_spaces(e):
    """{space -> vector} for an entity, tolerating legacy single-embedding entries."""
    embs = dict(e.get("embeddings") or {})
    if not embs and e.get("embedding"):
        embs = {"default": e["embedding"]}
    elif "default" not in embs and e.get("embedding"):
        embs["default"] = e["embedding"]
    return {sp: v for sp, v in embs.items() if v}


def _rank(entries, qv, mode):
    """Rank entity names for one query embedding under 'single' or 'multi' scoring."""
    scored = []
    for e in entries:
        per = {sp: _cos(qv, v) for sp, v in _entity_spaces(e).items()}
        if not per:
            continue
        score = per.get("default", 0.0) if mode == "single" \
            else combine_similarities(per, e.get("divergence_profile"))
        scored.append((e["name"], score))
    scored.sort(key=lambda x: -x[1])
    return [n for n, _ in scored]


def _metrics(ranked, relevant):
    return {
        "recall@5": recall_at_k(ranked, relevant, k=5),
        "recall@10": recall_at_k(ranked, relevant, k=10),
        "mrr": mrr(ranked, relevant),
        "ndcg@10": ndcg_at_k(ranked, relevant, k=10),
    }


def run_ablation(entries, query_set, embed_fn):
    """Single vs multi-space retrieval over `query_set` against `entries`.

    embed_fn(text) -> default-space query vector. Queries with empty 'relevant' are skipped (they
    can't contribute to recall averages). Returns single/multi/delta metric dicts + the verdict.
    """
    acc = {"single": {k: 0.0 for k in _KEYS}, "multi": {k: 0.0 for k in _KEYS}}
    n = 0
    for q in query_set:
        relevant = q.get("relevant") or []
        if not relevant:
            continue
        qv = embed_fn(q["query"])
        if not qv:
            continue
        n += 1
        for mode in ("single", "multi"):
            m = _metrics(_rank(entries, qv, mode), relevant)
            for k in _KEYS:
                acc[mode][k] += m[k]

    single = {k: round(acc["single"][k] / n, 4) if n else 0.0 for k in _KEYS}
    multi = {k: round(acc["multi"][k] / n, 4) if n else 0.0 for k in _KEYS}
    delta = {k: round(multi[k] - single[k], 4) for k in _KEYS}
    return {
        "n_queries": n,
        "n_entities": len(entries),
        "single": single,
        "multi": multi,
        "delta": delta,
        "mrr_lift": delta["mrr"],
        "threshold": MRR_LIFT_KEEP_THRESHOLD,
        "keep_multispace": delta["mrr"] >= MRR_LIFT_KEEP_THRESHOLD,
    }
