"""Attribution sampling — the steering signal for memory utility.

plan-memory-direction-2026 problem (c): telemetry proves memories are RETRIEVED
(94% strong hits) but not that they CHANGE work. The honest, code-only signal
available in this harness: a CITATION — the moment a `chain step --uses X` or
`remember --uses/--informs X` executes, X demonstrably influenced the current
work. Joining citations against the recall log yields per-memory attribution:

    recalled-and-then-cited  -> the memory earns its keep (utility proven)
    recalled-never-cited     -> retrieval noise or ambient value (review)
    cited-without-recall     -> ambient knowledge (L0/context carried it)

Forward-precise: citations are logged AT THE MOMENT they happen (this module).
Historical baseline: static backlink counts (relations have no timestamps).
No LLM calls anywhere; the dream pass consumes the report for its judgments,
and telemetry-derived importance can lean on attribution_rate over self-rating.
"""

import json
import os
from datetime import datetime, timezone

CITE_WINDOW_HOURS = 24   # a citation within this window of a recall counts as attributed


def _log_path(config):
    root = getattr(config, "project_root", None) or "."
    return os.path.join(str(root), ".memoryschema", "citation_log.jsonl")


def log_citation(config, source, targets, context=""):
    """Append citation events (best-effort, never blocks the caller)."""
    if not targets:
        return
    try:
        path = _log_path(config)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        with open(path, "a", encoding="utf-8") as f:
            for t in targets:
                f.write(json.dumps({"ts": now, "source": source, "target": t,
                                    "context": context}) + "\n")
    except Exception:
        pass


def read_citations(config):
    path = _log_path(config)
    events = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    return events


def compute_attribution(config):
    """Per-memory attribution from the recall log x citation log.

    Returns {name: {recalls, citations, attributed (citations within the
    window after a recall), attribution_rate, last_recalled, last_cited}}
    plus summary lists. Backlink-era citations (pre-log) are not counted in
    attributed/rate — the rate becomes meaningful as the logs accumulate.
    """
    from memoryschema.recall_log import read_events

    recalls = {}          # name -> [ts, ...]
    for ev in read_events(config):
        ts = ev.get("ts")
        for hit in ev.get("hits", []):
            n = hit.get("name")
            if n and ts:
                recalls.setdefault(n, []).append(ts)

    citations = {}        # name -> [ts, ...]
    for ev in read_citations(config):
        n = ev.get("target")
        if n and ev.get("ts"):
            citations.setdefault(n, []).append(ev["ts"])

    def _dt(s):
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None

    out = {}
    for name in set(recalls) | set(citations):
        r_ts = sorted(filter(None, (_dt(t) for t in recalls.get(name, []))))
        c_ts = sorted(filter(None, (_dt(t) for t in citations.get(name, []))))
        attributed = 0
        for r in r_ts:
            if any(0 <= (c - r).total_seconds() <= CITE_WINDOW_HOURS * 3600 for c in c_ts):
                attributed += 1
        out[name] = {
            "recalls": len(r_ts),
            "citations": len(c_ts),
            "attributed_recalls": attributed,
            "attribution_rate": round(attributed / len(r_ts), 3) if r_ts else None,
            "last_recalled": r_ts[-1].isoformat() if r_ts else None,
            "last_cited": c_ts[-1].isoformat() if c_ts else None,
        }

    summary = {
        "recalled_never_cited": sorted(
            (n for n, m in out.items() if m["recalls"] >= 3 and m["citations"] == 0),
            key=lambda n: -out[n]["recalls"]),
        "top_attributed": sorted(
            (n for n, m in out.items() if m["citations"] > 0),
            key=lambda n: (-(out[n]["attribution_rate"] or 0), -out[n]["citations"]))[:10],
    }
    return {"memories": out, "summary": summary}
