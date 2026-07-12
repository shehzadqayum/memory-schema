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


def _dt(s):
    """ISO timestamp → NAIVE datetime (or None). Normalizing to naive means a single tz-aware
    entry (an older writer, a manual repair, an external appender) can't raise TypeError on
    subtraction and crash the attribution join / dream report."""
    try:
        d = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    return d.replace(tzinfo=None) if d.tzinfo is not None else d


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


def _events_and_cites(config):
    """(events, cites): events = [(t0_naive, [hit names], regime)]; cites = {name: sorted naive dts}.
    `regime` = the stable-JSON of the recall event's retrieval-config snapshot ('pre-cfg' if absent)."""
    from memoryschema.recall_log import read_events
    cites = {}
    for ev in read_citations(config):
        n, ts = ev.get("target"), _dt(ev.get("ts"))
        if n and ts:
            cites.setdefault(n, []).append(ts)
    for n in cites:
        cites[n].sort()
    events = []
    for ev in read_events(config):
        t0 = _dt(ev.get("ts"))
        if t0 is None:
            continue
        names = [h.get("name") for h in ev.get("hits", []) if h.get("name")]
        cfg = ev.get("cfg")
        regime = json.dumps(cfg, sort_keys=True) if cfg else "pre-cfg"
        events.append((t0, names, regime))
    return events, cites


def _event_attributed(t0, names, cites, w_hours):
    """True if any of the event's hits earns a citation within w_hours AFTER the event."""
    limit = w_hours * 3600
    return any(any(0 <= (c - t0).total_seconds() <= limit for c in cites.get(n, []))
               for n in names)


def compute_aggregate(config, windows=(24, 72, 168)):
    """EVENT-level aggregate attribution — the single guardrail NUMBER the calibration workflow
    watches (harness-manual §7.3), NOT a loss function (attribution is censored implicit feedback).

    For each window W an event is 'attributed' if ANY of its served hits earns a citation within W
    hours; rate = attributed events / total events. Segmented by the recall-log retrieval-config
    snapshot ('cfg') so a config change's effect is legible; pre-snapshot events fall in 'pre-cfg'.
    Reporting at MULTIPLE windows makes any conclusion robust to the 24h join-window choice."""
    events, cites = _events_and_cites(config)
    regimes = sorted({r for _, _, r in events})
    overall, by_regime = {}, {r: {} for r in regimes}
    for w in windows:
        key = str(w)
        attr = sum(1 for t0, names, _ in events if _event_attributed(t0, names, cites, w))
        overall[key] = {"events": len(events), "attributed": attr,
                        "rate": round(attr / len(events), 3) if events else None}
        for r in regimes:
            evs = [(t0, names) for t0, names, rr in events if rr == r]
            a = sum(1 for t0, names in evs if _event_attributed(t0, names, cites, w))
            by_regime[r][key] = {"events": len(evs), "attributed": a,
                                 "rate": round(a / len(evs), 3) if evs else None}
    return {"windows": list(windows), "events": len(events),
            "overall": overall, "by_regime": by_regime}


def attribution_drift(config, window_hours=24, period_days=14, now=None):
    """Trailing-period vs prior-period event-level attribution rate — the DRIFT-ALARM input.

    Compares [now-P, now] against [now-2P, now-P) (P = period_days) at window W. Returns
    {recent, prior, rel_drop} where rel_drop = (prior-recent)/prior; None fields when a period has
    no events. A large drop means the current policy is surfacing less-cited memories than it was —
    a signal to INVESTIGATE (never to auto-tune; citation is Goodhart-vulnerable and nonstationary)."""
    events, cites = _events_and_cites(config)
    ref = _dt(now) if isinstance(now, str) else (
        now.replace(tzinfo=None) if isinstance(now, datetime) and now.tzinfo else now)
    if ref is None:
        ref = datetime.now(timezone.utc).replace(tzinfo=None)
    p = period_days * 86400

    def _rate(lo, hi):
        evs = [(t0, names) for t0, names, _ in events if lo <= (ref - t0).total_seconds() < hi]
        if not evs:
            return None, 0
        a = sum(1 for t0, names in evs if _event_attributed(t0, names, cites, window_hours))
        return round(a / len(evs), 3), len(evs)

    recent, n_recent = _rate(0, p)
    prior, n_prior = _rate(p, 2 * p)
    rel_drop = round((prior - recent) / prior, 3) if (prior and recent is not None and prior > 0) else None
    return {"window_hours": window_hours, "period_days": period_days,
            "recent": recent, "recent_events": n_recent,
            "prior": prior, "prior_events": n_prior, "rel_drop": rel_drop}
