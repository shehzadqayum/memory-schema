"""Calibration toolkit — the measurement seams for tuning epistemic policy safely.

From the gate-tuning evaluation (memory: gate-tuning-evaluation): the attribution join is a
GUARDRAIL, not a loss function (censored implicit feedback), so tuning weight belongs on
(a) a curated gold fixture suite grown from real logged queries (gold_candidates → operator
review → eval-gold.jsonl), and (b) paired within-query replay: the SAME queries re-scored
under config A vs config B, compared per-query (high statistical power at low n — a
between-cell attribution-rate A/B would need ~710 recalls per 10pp effect).

Everything here is READ-ONLY over the store and telemetry: these functions PROPOSE numbers;
the operator applies TOML changes one at a time, in git. The loop never closes automatically.
"""
import json
import math
from dataclasses import replace

from memoryschema.inheritance import _TOML_FIELD_MAP


# ── config overrides (the grid-cell mechanism) ────────────────────────────────────────────

def parse_overrides(pairs, config):
    """Parse ["retrieval.recency_decay=0.99", ...] → {field: typed value}.

    Keys are TOML keys (the operator-facing names); values are coerced to the type of the
    current config field, so a bad key or value fails LOUDLY before any store is touched.
    """
    out = {}
    for raw in (pairs or []):
        key, sep, val = str(raw).partition("=")
        key = key.strip()
        if not sep:
            raise ValueError(f"override needs key=value: {raw!r}")
        field = _TOML_FIELD_MAP.get(key)
        if field is None:
            raise ValueError(f"unknown config key {key!r} (see docs/parameter-registry.md)")
        cur = getattr(config, field)
        val = val.strip()
        if isinstance(cur, bool):                      # before int: bool is an int subclass
            out[field] = val.lower() in ("1", "true", "yes", "on")
        elif isinstance(cur, int):
            out[field] = int(val)
        elif isinstance(cur, float):
            out[field] = float(val)
        elif isinstance(cur, tuple):
            out[field] = tuple(float(x) for x in val.split(","))
        else:
            out[field] = val
    return out


def apply_overrides(config, pairs):
    """New MemoryConfig with the given key=value overrides applied (original untouched)."""
    fields = parse_overrides(pairs, config)
    return replace(config, **fields) if fields else config


# ── paired statistics ─────────────────────────────────────────────────────────────────────

def sign_test_p(wins, losses):
    """Exact two-sided sign test (binomial, p=0.5) on paired win/loss counts. Ties excluded
    by the caller. Returns 1.0 when there is no discordant pair (no evidence either way)."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


# ── gold-set growth (candidates for OPERATOR review — never auto-labels) ─────────────────

def gold_candidates(config, window_hours=None):
    """Candidate {query → relevant memory} pairs mined from the attribution join: a recall
    whose hit was cited within the window is weak evidence the memory answered the query.
    These are CANDIDATES for the operator to verify into eval-gold.jsonl — usage labels
    inherit position/selection bias and must not become the objective unreviewed."""
    from memoryschema.recall_log import read_events
    from memoryschema.attribution import read_citations, CITE_WINDOW_HOURS
    window = float(window_hours or CITE_WINDOW_HOURS)

    def _dt(s):
        from datetime import datetime
        try:
            d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
            return d.replace(tzinfo=None)
        except Exception:
            return None

    cites = {}
    for c in read_citations(config):
        t = _dt(c.get("ts"))
        if t is not None and c.get("target"):
            cites.setdefault(c["target"], []).append(t)

    agg = {}
    for ev in read_events(config):
        t0 = _dt(ev.get("ts"))
        q = (ev.get("query") or "").strip()
        if t0 is None or not q:
            continue
        for h in ev.get("hits") or []:
            name = h.get("name")
            if not name or name not in cites:
                continue
            if any(0 <= (ct - t0).total_seconds() / 3600 <= window for ct in cites[name]):
                key = (q, name)
                agg[key] = agg.get(key, 0) + 1
    rows = [{"query": q, "relevant": [n], "kind": "attribution-candidate", "evidence": c}
            for (q, n), c in agg.items()]
    rows.sort(key=lambda r: (-r["evidence"], r["query"]))
    return rows


# ── paired within-query replay (the tuning engine) ────────────────────────────────────────

def replay(config, a_pairs, b_pairs, k=5, source="both"):
    """Re-run the SAME queries under config A (--set, default = deployment) and config B
    (--vs) against the CURRENT JSONL store; compare per-query. Label-free diff for logged
    queries; win/loss + exact sign test where gold labels exist. (Historical-state replay —
    rebuilding store+embeddings from a git commit — is deliberately out of scope here.)"""
    from memoryschema.store import MemoryStore
    from memoryschema.recall_log import read_events
    from memoryschema.eval.fixtures import load_gold_set

    cfg_a = apply_overrides(config, a_pairs)
    cfg_b = apply_overrides(config, b_pairs)
    store_a = MemoryStore(str(config.store_path), config=cfg_a)
    store_b = MemoryStore(str(config.store_path), config=cfg_b)

    def _topk(store, cfg, query):
        rows = store.recall(query=query, limit=k,
                            depth=cfg.recall_depth, decay=cfg.recall_decay)
        return [r.get("name") for r in rows]

    out = {"k": k, "a": parse_overrides(a_pairs, config), "b": parse_overrides(b_pairs, config),
           "logged": None, "gold": None}

    if source in ("log", "both"):
        seen, queries = set(), []
        for ev in read_events(config):
            q = (ev.get("query") or "").strip()
            if q and q not in seen:
                seen.add(q)
                queries.append(q)
        per, jacc_sum = [], 0.0
        for q in queries:
            a, b = _topk(store_a, cfg_a, q), _topk(store_b, cfg_b, q)
            sa, sb = set(a), set(b)
            union = sa | sb
            jacc = (len(sa & sb) / len(union)) if union else 1.0
            jacc_sum += jacc
            if sa != sb:
                per.append({"query": q, "entered": sorted(sb - sa), "left": sorted(sa - sb),
                            "jaccard": round(jacc, 3)})
        out["logged"] = {"queries": len(queries), "changed": len(per),
                         "mean_jaccard": round(jacc_sum / len(queries), 3) if queries else None,
                         "diffs": per}

    if source in ("gold", "both"):
        # ONLY the project's own curated gold file — load_gold_set falls back to the packaged
        # dev-history fixtures, whose labels name the PACKAGE's entities, not this deployment's.
        gold_path = config.project_root / "eval-gold.jsonl"
        try:
            gold = load_gold_set(gold_path) if gold_path.is_file() else []
        except Exception:
            gold = []
        if gold:
            hits_a = hits_b = b01 = b10 = 0
            rank_w = rank_l = 0
            for g in gold:
                rel = set(g.get("relevant") or [])
                a, b = _topk(store_a, cfg_a, g["query"]), _topk(store_b, cfg_b, g["query"])
                ha, hb = bool(rel & set(a)), bool(rel & set(b))
                hits_a += ha
                hits_b += hb
                if not ha and hb:
                    b01 += 1
                elif ha and not hb:
                    b10 += 1
                ra = min((a.index(n) for n in rel if n in a), default=k)
                rb = min((b.index(n) for n in rel if n in b), default=k)
                if rb < ra:
                    rank_w += 1
                elif ra < rb:
                    rank_l += 1
            out["gold"] = {"queries": len(gold),
                           "hits_a": hits_a, "hits_b": hits_b,
                           "mcnemar": {"b_only": b01, "a_only": b10,
                                       "p": round(sign_test_p(b01, b10), 4)},
                           "rank": {"b_wins": rank_w, "a_wins": rank_l,
                                    "p": round(sign_test_p(rank_w, rank_l), 4)}}
        else:
            out["gold"] = {"queries": 0, "note": "no eval-gold.jsonl — run goldgen + curate"}
    return out


# ── decay-form fit (Anderson & Schooler: the environment picks the form) ─────────────────

def fit_decay(config, min_intervals=50):
    """Fit the inter-recall interval distribution from the recall log: exponential vs
    power-law CCDF (R² in each model's linear space). The recall log IS the environment's
    need-probability statistics (Anderson & Schooler 1991) — the decay FORM should come from
    here, not from a grid search against a proxy. Read-only; honest below min_intervals."""
    from memoryschema.recall_log import read_events

    def _dt(s):
        from datetime import datetime
        try:
            return datetime.fromisoformat(str(s).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None

    by_name = {}
    for ev in read_events(config):
        t = _dt(ev.get("ts"))
        if t is None:
            continue
        for h in ev.get("hits") or []:
            if h.get("name"):
                by_name.setdefault(h["name"], []).append(t)
    intervals = []
    for ts in by_name.values():
        ts.sort()
        intervals.extend((b - a).total_seconds() / 3600 for a, b in zip(ts, ts[1:]))
    intervals = sorted(i for i in intervals if i > 0)
    n = len(intervals)
    out = {"n_intervals": n, "min_required": min_intervals}
    if n < min_intervals:
        out["verdict"] = (f"insufficient data ({n} < {min_intervals} intervals) — keep the "
                          f"current form; re-run as the log grows")
        return out

    med = intervals[n // 2]
    ccdf = [(t, 1 - i / n) for i, t in enumerate(intervals) if 1 - i / n > 0]

    def _r2(xs, ys, fx):
        mean = sum(ys) / len(ys)
        ss_tot = sum((y - mean) ** 2 for y in ys) or 1e-12
        ss_res = sum((y - fx(x)) ** 2 for x, y in zip(xs, ys))
        return 1 - ss_res / ss_tot

    # exponential: ln S(t) = -λt (through origin)
    xs = [t for t, _ in ccdf]
    ys = [math.log(s) for _, s in ccdf]
    lam = -sum(x * y for x, y in zip(xs, ys)) / (sum(x * x for x in xs) or 1e-12)
    r2_exp = _r2(xs, ys, lambda x: -lam * x)
    # power law: ln S = -α ln t + c (t > 0)
    lx = [math.log(t) for t, _ in ccdf]
    mx, my = sum(lx) / len(lx), sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in lx) or 1e-12
    alpha = sum((x - mx) * (y - my) for x, y in zip(lx, ys)) / denom
    c = my - alpha * mx
    r2_pow = _r2(lx, ys, lambda x: alpha * x + c)

    hourly = math.exp(-lam)
    out.update({
        "median_interval_h": round(med, 1),
        "exponential": {"lambda_per_h": round(lam, 5), "equiv_recency_decay": round(hourly, 5),
                        "r2": round(r2_exp, 3)},
        "power_law": {"alpha": round(-alpha, 3), "r2": round(r2_pow, 3)},
        "verdict": ("power-law CCDF fits better — consider a power-law/type-conditioned "
                    "recency form (Anderson & Schooler)" if r2_pow > r2_exp + 0.05 else
                    "exponential adequate at this n — the fitted equiv_recency_decay is the "
                    "environment-derived base" if r2_exp >= r2_pow else
                    "fits comparable — insufficient contrast; keep current form"),
    })
    return out
