"""Dream-pass candidate report — the CODE half of the consolidation loop.

plan-memory-direction-2026: the dream pass is a scheduled session in which the
LLM exercises JUDGMENT (what to distill, merge, refresh) using only the safe
write primitives (remember / --supersedes / archive / set_lifecycle). This
module supplies the DISCOVERY: a deterministic, read-only report of
consolidation candidates. Code finds; the LLM decides; existing primitives act.

Candidate classes:
  chains      — released (not active) chains still status=active: distillation
                candidates (their durable lessons should become standalone
                entities, then the chain archived — archive-never-destroy).
  oversized   — the ACTIVE chain past the rotation threshold (obs count).
  stale_keyed — keyed facts valid_from older than N days and never superseded:
                the holder may be outdated (surface for review, never auto-act).
  never_surfaced — active entities with zero recall-log appearances over the
                observed window (dead-weight/archival candidates).
  duplicates  — active entity pairs with default-embedding cosine above a
                threshold (merge candidates).
"""

import json
import os
from datetime import date, datetime, timezone

DUP_COSINE = 0.80
STALE_DAYS = 14
CHAIN_OBS_ROTATION = 40


def _load_entries(store_path):
    entries = []
    if not os.path.exists(store_path):
        return entries
    with open(store_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


def build_report(config, active_chain=None, today=None):
    """Assemble the candidate report (pure read; no writes, no API calls).

    Vectors come from the store entries (rehydrated from the sidecar by the
    normal load path). Returns a dict of candidate lists, each item carrying
    enough context for the dream session to judge without re-deriving.
    """
    store_path = str(config.store_path)
    entries = _load_entries(store_path)
    # sidecar rehydration happens in MemoryStore._load; raw json lines carry
    # the external marker instead — rehydrate here for the duplicate scan.
    try:
        from memoryschema.vector_sidecar import rehydrate, sidecar_dir
        sdir = sidecar_dir(store_path)
        for e in entries:
            rehydrate(e, sdir)
    except Exception:
        pass

    today = today or date.today().isoformat()
    active = [e for e in entries if (e.get("status") or "active") == "active"]

    report = {"generated": today, "counts": {}, "chains": [], "oversized": [],
              "stale_keyed": [], "never_surfaced": [], "duplicates": []}

    # 1. Released-but-active chains -> distillation candidates
    for e in active:
        name = e.get("name", "")
        if not name.startswith("chain-"):
            continue
        n_obs = len(e.get("observations") or [])
        if name == active_chain:
            if n_obs > CHAIN_OBS_ROTATION:
                report["oversized"].append({
                    "name": name, "observations": n_obs,
                    "note": "active chain past the rotation threshold (%d) — "
                            "conclude + release + start a successor soon" % CHAIN_OBS_ROTATION})
            continue
        report["chains"].append({
            "name": name, "observations": n_obs,
            "description": (e.get("description") or "")[:140],
            "note": "released chain, never distilled — extract durable lessons "
                    "into standalone entities, then archive it"})

    # 2. Stale keyed facts
    for e in active:
        key = e.get("key")
        vf = e.get("valid_from")
        if not key or not vf:
            continue
        try:
            age = (datetime.fromisoformat(today) - datetime.fromisoformat(vf)).days
        except ValueError:
            continue
        if age >= STALE_DAYS:
            report["stale_keyed"].append({
                "name": e["name"], "key": key, "valid_from": vf, "age_days": age,
                "note": "keyed fact unrefreshed for %dd — still true? re-remember "
                        "with the same key to refresh, or leave if stable" % age})

    # 3. Never-surfaced actives (recall-log window)
    try:
        from memoryschema.recall_log import read_events
        events = read_events(config)
        surfaced = set()
        for ev in events:
            for r in ev.get("hits", ev.get("results", [])):   # log schema uses "hits"
                n = r.get("name") if isinstance(r, dict) else None
                if n:
                    surfaced.add(n)
        if events:
            for e in active:
                name = e.get("name", "")
                if name and name not in surfaced and not name.startswith("chain-"):
                    report["never_surfaced"].append({
                        "name": name,
                        "description": (e.get("description") or "")[:120],
                        "note": "zero recall appearances in the logged window — "
                                "archive if resolved/expired, keep if reference"})
    except Exception:
        pass

    # 4. Near-duplicate pairs (default-space cosine over actives)
    vecs = [(e["name"], e.get("embedding")) for e in active if e.get("embedding")]
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            c = _cos(vecs[i][1], vecs[j][1])
            if c >= DUP_COSINE:
                report["duplicates"].append({
                    "a": vecs[i][0], "b": vecs[j][0], "cosine": round(c, 3),
                    "note": "high overlap — merge (new entity --supersedes both) "
                            "or link if genuinely distinct"})
    report["duplicates"].sort(key=lambda d: -d["cosine"])

    report["counts"] = {k: len(v) for k, v in report.items()
                        if isinstance(v, list)}
    return report
