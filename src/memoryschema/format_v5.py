"""Schema v5: YAML frontmatter (machine scalars) + markdown body (prose).

The v5 design principle (plan-memory-v5-sota-alignment): PROSE NEVER ENTERS THE
STRUCTURED LAYER. Frontmatter holds only machine fields; every prose field lives
in the markdown body under heading conventions — so the entire XML-escaping
corruption class (M14) is impossible by construction, chain updates are
single-line appends, and the format matches the wiki markdown the LLM already
writes correctly every day.

File shape:

    ---
    schema: 5
    type: semantic            # optional
    importance: 7             # optional
    status: active            # optional
    project: helios           # optional
    relations:
      - USES some-memory
      - SUPERSEDES old-memory
    ---

    One-line description (the first body paragraph; keep it short).

    ## Summary
    The evolving summary (unbounded; replaces v4's description-abuse on chains).

    ## Observations
    - one atomic fact per bullet

    ## Log
    - Step 1: chain steps, append-only, one per bullet

    ## Reasoning
    Narrative prose. Appended to over time.

    ## Prompt
    The original trigger.

    ## Chain
    Chain context line.

Parsing returns the SAME dict shape the v4 parser produces, so every downstream
consumer (stores, scoring, embedding, gate, L0) works unchanged:
- name comes from the FILENAME (v5 drops the redundant name attribute),
- description = the first paragraph,
- observations = Observations bullets + Log bullets (the file keeps them
  distinct; the index view flattens — chains keep today's recall semantics,
  including the recency-biased embedding of the newest steps),
- 'summary' and 'log' are ALSO kept as their own keys for writers/embedding.

The frontmatter parser is a deliberate mini-subset of YAML (scalars + one list
of strings) — zero dependencies, and prose can never break it because prose
never goes there.
"""

import os
import re

FRONTMATTER_OPEN = "---"
_SECTIONS = ("summary", "observations", "log", "reasoning", "prompt", "chain")
_REL_RE = re.compile(r"^-\s+([A-Z_]+)\s+([A-Za-z0-9][A-Za-z0-9-]*)\s*$")


def is_v5_content(content):
    """A v5 file starts with a '---' frontmatter fence."""
    return content.lstrip().startswith(FRONTMATTER_OPEN + "\n") or \
        content.lstrip().startswith(FRONTMATTER_OPEN + "\r\n") or \
        content.lstrip() == FRONTMATTER_OPEN


def _parse_frontmatter(lines):
    """Mini YAML subset: `key: scalar` + `relations:` followed by `- TYPE target`.
    Returns (dict, relations list). Unknown keys are kept as strings."""
    meta = {}
    relations = []
    in_relations = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if in_relations:
            m = _REL_RE.match(line.strip())
            if m:
                relations.append({"type": m.group(1), "target": m.group(2)})
                continue
            in_relations = False  # fall through to key parsing
        if line.strip() == "relations:":
            in_relations = True
            continue
        if ":" in line and not line.startswith((" ", "-")):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, relations


def parse_v5_content(content, filepath=None):
    """Parse v5 content into the standard memory dict. Returns None only when
    the frontmatter fence is absent/unterminated (not a v5 entity)."""
    text = content.lstrip("﻿")  # BOM tolerance
    stripped = text.lstrip()
    if not is_v5_content(stripped):
        return None
    lines = stripped.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_OPEN:
        return None
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == FRONTMATTER_OPEN)
    except StopIteration:
        return None  # unterminated fence

    meta, relations = _parse_frontmatter(lines[1:close])
    # The explicit discriminator: v5 entities declare `schema: 5`. Ordinary
    # YAML-frontmatter markdown (wiki notes, templates) parses as None — the
    # v4-era contract that non-entity files are skipped stays intact.
    if str(meta.get("schema", "")).strip() != "5":
        return None
    body_lines = lines[close + 1:]

    # Split the body into the lead paragraph + ## sections.
    sections = {}
    current = "_lead"
    buf = {current: []}
    for line in body_lines:
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            buf.setdefault(current, [])
            continue
        buf[current].append(line)
    for key, blines in buf.items():
        sections[key] = "\n".join(blines).strip()

    def bullets(section):
        out = []
        for line in (sections.get(section) or "").splitlines():
            s = line.strip()
            if s.startswith("- "):
                out.append(s[2:].strip())
            elif s and out:                      # continuation line of the previous bullet
                out[-1] += " " + s
        return out

    lead = sections.get("_lead", "")
    description = lead.split("\n\n")[0].replace("\n", " ").strip()

    name = meta.get("name")
    if not name and filepath:
        name = os.path.splitext(os.path.basename(str(filepath)))[0]
    if not name:
        return None

    obs = bullets("observations")
    log = bullets("log")

    memory = {
        "schema": int(meta.get("schema", 5) or 5),
        "name": name,
        "description": description,
        "observations": obs + log,          # flattened index view (file keeps them distinct)
        "summary": sections.get("summary") or None,
        "log": log or None,
        "reasoning": sections.get("reasoning") or None,
        "prompt": sections.get("prompt") or None,
        "chain": sections.get("chain") or None,
        "relations": relations,
        "type": meta.get("type") or "semantic",
        "status": meta.get("status") or "active",
        "body": sections.get("notes") or None,   # trailing human notes (v4 body-after-entity parity)
    }
    if meta.get("importance"):
        try:
            memory["importance"] = int(meta["importance"])
        except ValueError:
            pass
    if meta.get("project"):
        memory["project"] = meta["project"]
    # Temporal validity + fact-key (plan-memory-direction-2026): key = the fact
    # identity for deterministic write-time supersession; valid_from/superseded_at
    # bound the validity interval; superseded_by names the successor.
    for tk in ("key", "valid_from", "superseded_at", "superseded_by", "promoted_to"):
        if meta.get(tk):
            memory[tk] = meta[tk]
    # drop empty optionals for dict-shape parity with the v4 parser
    return {k: v for k, v in memory.items() if v is not None}


def serialize_v5(memory):
    """Serialize a memory dict to v5 file content. Plain text in, valid file out —
    there is nothing to escape because prose never enters the structured layer."""
    NL = "\n"
    out = [FRONTMATTER_OPEN, "schema: 5"]
    for key in ("type", "importance", "status", "project",
                "key", "valid_from", "superseded_at", "superseded_by", "promoted_to"):
        val = memory.get(key)
        if val is not None and val != "" and not (key == "type" and val == "semantic") \
                and not (key == "status" and val == "active"):
            out.append("%s: %s" % (key, val))
    rels = memory.get("relations") or []
    if rels:
        out.append("relations:")
        for r in rels:
            rtype = r.get("type") if isinstance(r, dict) else r[0]
            target = r.get("target") if isinstance(r, dict) else r[1]
            out.append("  - %s %s" % (rtype, target))
    out.append(FRONTMATTER_OPEN)
    out.append("")
    out.append((memory.get("description") or "").strip())

    def section(title, text):
        if text:
            out.extend(["", "## " + title, "", text.strip()])

    def bullet_section(title, items):
        if items:
            out.extend(["", "## " + title, ""])
            out.extend("- " + str(i).strip() for i in items)

    section("Summary", memory.get("summary"))
    # observations minus log entries = the atomic facts (avoid duplicating steps)
    log = list(memory.get("log") or [])
    obs = [o for o in (memory.get("observations") or []) if o not in log]
    bullet_section("Observations", obs)
    bullet_section("Log", log)
    section("Reasoning", memory.get("reasoning"))
    section("Prompt", memory.get("prompt"))
    section("Chain", memory.get("chain"))
    section("Notes", memory.get("body"))
    return NL.join(out).rstrip() + NL
