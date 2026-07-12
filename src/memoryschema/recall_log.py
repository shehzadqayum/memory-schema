"""Recall usage telemetry — turn "is memory actually READ?" into a measurement.

Move 1 of plan-memory-value-measurement: the store tracked access_count=0 for everything, so the
central value claim ("memory helps the next session") was unmeasured. This appends one line per
recall to a runtime log (SEPARATE from scoring — it never touches access_count or ranking), and a
reader summarises usage: how often recall runs, whether it returns strong hits, which memories
surface, and which never do (dead-weight candidates).

Honest limit: this measures RETRIEVAL, not UTILITY (whether the recalled memory changed the answer
needs response-attribution — a later, second-order metric).


"""
import json
import os
from pathlib import Path


def _log_path(config):
    # Runtime telemetry lives outside memory/ (the content dir holds only entities). .memoryschema/
    # is gitignored.
    return Path(config.project_root) / ".memoryschema" / "recall_log.jsonl"


def _disabled():
    # Opt-out for tests/automation so they never pollute a real project's log.
    return os.environ.get("MEMORYSCHEMA_RECALL_LOG") == "0"


def log_recall(config, query, results, backend, degraded=False, now=None):
    """Best-effort: append one recall event. NEVER raises (telemetry must not break recall)."""
    if _disabled():
        return
    try:
        if now is None:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
        hits = [{"name": r.get("name"),
                 "score": round(float(r.get("score") or 0), 4),
                 "channel": r.get("channel")}
                for r in (results or [])][:10]
        rec = {"ts": now, "query": query, "n": len(results or []),
               "backend": backend, "degraded": bool(degraded), "hits": hits}
        # Snapshot the active retrieval config per event — without it a config change is invisible
        # in the telemetry and attribution can never be segmented by config regime (gate-tuning eval).
        try:
            rec["cfg"] = {"recency_decay": config.recency_decay,
                          "recall_depth": config.recall_depth,
                          "recall_decay": config.recall_decay,
                          "semantic_weights": list(config.semantic_weights)}
        except Exception:
            pass                        # telemetry stays best-effort; a partial event beats none
        p = _log_path(config)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_events(config):
    """All logged recall events (skips malformed lines)."""
    p = _log_path(config)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def compute_stats(config, strong=0.5, known_names=None):
    """Summarise recall usage. `known_names` (the full entity name-set) enables the never-surfaced
    (dead-weight) report."""
    from collections import Counter
    ev = read_events(config)
    n = len(ev)
    with_results = sum(1 for e in ev if e.get("n"))
    strong_hits = sum(1 for e in ev
                      if e.get("hits") and (e["hits"][0].get("score") or 0) >= strong)
    degraded = sum(1 for e in ev if e.get("degraded"))
    surfaced = Counter()
    for e in ev:
        for h in e.get("hits", []):
            if h.get("name"):
                surfaced[h["name"]] += 1
    days = sorted({(e.get("ts") or "")[:10] for e in ev if e.get("ts")})
    stats = {
        "events": n,
        "with_results": with_results,
        "strong_hits": strong_hits,
        "strong_hit_rate": round(strong_hits / n, 3) if n else 0.0,
        "degraded": degraded,
        "distinct_days": len(days),
        "recalls_per_day": round(n / len(days), 2) if days else 0.0,
        "top_surfaced": surfaced.most_common(10),
    }
    if known_names is not None:
        never = sorted(set(known_names) - set(surfaced))
        stats["never_surfaced_count"] = len(never)
        stats["never_surfaced"] = never[:20]
    return stats
