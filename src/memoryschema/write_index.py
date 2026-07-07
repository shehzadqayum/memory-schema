"""Shared write-and-index pipeline + safe entity writers.

The deterministic write path: the LLM (or any caller) supplies PLAIN TEXT;
this module supplies structure — XML escaping, step numbering, anchored
appends with parse-validation + rollback, and the full index pipeline
(embed -> gate -> Neo4j + JSONL dual-write -> L0 rebuild -> sentinel).

Rationale (plan-memory-v5-sota-alignment): hand-authored XML corrupted the
store twice (the M14 class — a raw '<'/'&' in prose silently truncates the
parse). No serious 2025+ memory system has the LLM hand-author escaped
markup; content belongs to the model, structure belongs to code.

The pipeline here mirrors hooks/hook-post-write.sh (which remains the safety
net for hand-edited files); the CLI commands in cli/chain_cmd.py and
cli/memory_cmd.py call this directly and self-index, so a CLI write never
depends on the PostToolUse hook firing.

One deliberate improvement over the hook: DUAL-WRITE. The hook writes Neo4j
OR falls back to JSONL, so store.jsonl lags Neo4j until the next reconcile
(the recurring 'missing from JSONL (1)' drift). index_memory() writes BOTH
so the layers stay converged write-by-write.
"""

import os
import re
import sys
from xml.sax.saxutils import escape as _xml_escape


def escape_text(text):
    """XML-escape plain text for insertion into an entity element OR attribute.

    The single chokepoint that makes the M14 corruption class impossible on
    the CLI path: '<', '>', '&', and '"' become entities before they ever
    touch the file. The quote matters: attribute values (name, type, relation
    target/type) live in double-quoted contexts, so an un-escaped '"' would
    silently truncate the value and inject arbitrary attributes that still
    parse as well-formed XML (e.g. name='inj" status="superseded'). Escaping
    '"' everywhere is harmless for element text ('&quot;' round-trips to '"').
    """
    return _xml_escape(str(text), {'"': "&quot;"})


class IndexResult:
    """Outcome of index_memory: where it landed, what degraded, what warned."""

    def __init__(self):
        self.ok = False
        self.indexed_to = []       # ['neo4j', 'jsonl']
        self.embedded = False
        self.warnings = []         # gate warnings + advisory notes
        self.errors = []           # fatal reasons when ok is False
        self.verdict = None        # gate verdict string

    def summary(self):
        parts = []
        if self.ok:
            parts.append("indexed: " + "+".join(self.indexed_to or ["nowhere"]))
            parts.append("embedded" if self.embedded else "UNEMBEDDED")
        else:
            parts.append("FAILED: " + "; ".join(self.errors or ["unknown"]))
        if self.verdict and self.verdict != "accept":
            parts.append("gate=" + str(self.verdict))
        return " · ".join(parts)


def index_memory(filepath, config=None, require_active_chain_auth=True):
    """Parse, authorize, embed, gate, dual-write, and L0-rebuild one memory file.

    Returns IndexResult. Never raises for expected degradations (Neo4j down,
    Voyage missing) — those land in warnings; structural failures land in
    errors with ok=False.
    """
    from memoryschema.tags import parse_memory_file
    from memoryschema.chain_state import get_active_chain

    res = IndexResult()
    filepath = os.path.abspath(str(filepath))
    norm = filepath.replace("\\", "/")
    if "/memory/" not in norm:
        res.errors.append("not under a memory/ directory: %s" % filepath)
        return res
    project_root = norm.rsplit("/memory/", 1)[0]
    store_path = os.path.join(project_root, "memory", "store.jsonl")

    memory = parse_memory_file(filepath)
    if memory is None:
        res.errors.append("file failed to parse as a memory entity (corruption?)")
        return res
    name = memory.get("name", "")

    # Authorization: existing entities are read-only unless they are the active chain.
    if require_active_chain_auth:
        active = get_active_chain(project_root=project_root)
        exists = False
        if os.path.exists(store_path):
            import json as _json
            with open(store_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        if _json.loads(line).get("name") == name:
                            exists = True
                            break
                    except Exception:
                        continue
        if exists and name != active:
            res.errors.append("BLOCKED: %s is read-only (not the active chain)" % name)
            return res

    if config is None:
        try:
            from memoryschema.config import MemoryConfig
            config = MemoryConfig(project_root=project_root)
        except Exception:
            config = None

    jsonl_store = None
    try:
        from memoryschema.store import MemoryStore
        jsonl_store = MemoryStore(store_path)
    except Exception as e:
        res.warnings.append("jsonl store unavailable: %s" % e)

    # Embed (all spaces) — failure degrades, never blocks.
    voyage_key = os.environ.get("VOYAGE_API_KEY") or (
        getattr(config, "voyage_api_key", None) if config else None)
    if voyage_key:
        try:
            from memoryschema.spaces import embed_all_spaces
            from memoryschema.embedding_input import embed_input_hash
            embeddings, div_profile = embed_all_spaces(memory, config=config)
            if embeddings:
                memory["embedding"] = embeddings.get("default")
                memory["embeddings"] = embeddings
                if div_profile:
                    memory["divergence_profile"] = div_profile
                memory["embed_input_hash"] = embed_input_hash(memory)
                res.embedded = True
        except Exception as e:
            res.warnings.append("embedding failed (indexed unembedded): %s" % e)
    else:
        res.warnings.append("no VOYAGE_API_KEY — indexed unembedded")

    # Write gate.
    try:
        from memoryschema.write_gate import gate_pipeline, GateVerdict
        gate = gate_pipeline(memory, store=jsonl_store, config=config)
        res.warnings.extend(str(w) for w in gate.warnings)
        res.verdict = getattr(gate.verdict, "value", str(gate.verdict))
        if gate.verdict == GateVerdict.REJECT:
            res.errors.append("write gate REJECTED: " + "; ".join(str(r) for r in gate.reasons))
            return res
        if gate.verdict == GateVerdict.QUARANTINE:
            memory["status"] = "quarantined"
            memory.pop("embedding", None)
            memory.pop("embeddings", None)
            memory.pop("divergence_profile", None)
            res.embedded = False
            res.warnings.append("QUARANTINED: " + "; ".join(str(r) for r in gate.reasons))
    except ImportError:
        pass

    # Dual-write: Neo4j AND JSONL (keeps the layers converged write-by-write).
    l0_source_store = None
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        ns = Neo4jMemoryStore()
        ns.upsert(memory)
        if memory.get("embedding"):
            ns.compute_associations_single(name)
        res.indexed_to.append("neo4j")
        l0_source_store = ns
    except Exception as e:
        res.warnings.append("neo4j unavailable (JSONL only): %s" % type(e).__name__)
    if jsonl_store is not None:
        try:
            jsonl_store.upsert(memory)
            jsonl_store.compute_backlinks()
            if memory.get("embedding"):
                jsonl_store.compute_associations()
            res.indexed_to.append("jsonl")
            if l0_source_store is None:
                l0_source_store = jsonl_store
        except Exception as e:
            res.warnings.append("jsonl upsert failed: %s" % e)

    if not res.indexed_to:
        res.errors.append("both stores failed")
        return res

    # L0 rebuild (regenerate from the active set) — never blocks.
    try:
        from memoryschema.l0_budget import rebuild_index
        index_path = os.path.join(project_root, "memory", "MEMORY.md")
        budget = getattr(config, "l0_token_budget", 2000) if config else 2000
        active = l0_source_store.list_all(include_inactive=False)
        rebuild_index(index_path, entries=active, token_budget=budget)
    except Exception as e:
        res.warnings.append("L0 rebuild failed: %s" % e)

    # Stop-hook sentinel: a memory write happened this response. Write it under the
    # PROJECT root (not POSIX /tmp): native Python on Windows resolves "/tmp" to C:\tmp,
    # a different directory from the Git Bash hook's /tmp, so a CLI chain-step's sentinel
    # was invisible to hook-stop.sh -> a false "chain NOT updated" reminder every turn.
    # The Stop hook (cwd = project root) reads the same project-relative path.
    try:
        sentinel_dir = os.path.join(project_root, ".memoryschema")
        os.makedirs(sentinel_dir, exist_ok=True)
        with open(os.path.join(sentinel_dir, "chain-updated"), "w") as f:
            f.write(name)
    except Exception:
        pass

    res.ok = True
    return res


# ── Safe entity writers (string surgery with parse-validation + rollback) ──────

_OBS_CLOSE = "</memory:observations>"
_REASON_CLOSE = "</memory:reasoning>"
_RELS_CLOSE = "</memory:relations>"
_DESC_RE = re.compile(r"(<memory:description>).*?(</memory:description>)", re.DOTALL)


def _validate_or_rollback(filepath, new_content, old_content):
    """Write new_content; if it no longer parses as an entity, restore old_content."""
    from memoryschema.tags import parse_memory_content
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    if parse_memory_content(new_content) is None:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(old_content)
        raise ValueError("post-write parse failed — file rolled back unchanged")


def append_chain_step(filepath, step_text, desc=None, reasoning=None, uses=None):
    """Append one auto-numbered step to a chain entity, with optional description
    replacement, reasoning append (after a '---' separator) and USES relations.

    All text arguments are PLAIN TEXT — v4 files get escaping here; v5 files
    need none (prose never enters the structured layer). The result is
    parse-validated; on any structural failure the file is rolled back.
    Returns the step number written.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    original = content

    from memoryschema.format_v5 import is_v5_content
    if is_v5_content(content):
        return _append_chain_step_v5(filepath, content, original, step_text,
                                     desc=desc, reasoning=reasoning, uses=uses)

    # Auto-number: continue from the highest existing "Step N:" (falls back to the
    # observation count when no step-prefixed observations exist yet). Numbering by
    # max-step keeps the narrative sequence even when early observations are unprefixed.
    steps = [int(m) for m in re.findall(r"<memory:observation>\s*Step\s+(\d+)\s*:", content)]
    n_obs = content.count("<memory:observation>")
    step_no = (max(steps) if steps else n_obs) + 1
    text = step_text.strip()
    if not re.match(r"^(Step\s+\d+|Conclusion)\s*:", text, re.IGNORECASE):
        text = "Step %d: %s" % (step_no, text)

    if _OBS_CLOSE not in content:
        raise ValueError("no <memory:observations> block found in %s" % filepath)
    obs_xml = "    <memory:observation>%s</memory:observation>\n  " % escape_text(text)
    content = content.replace(_OBS_CLOSE, obs_xml + _OBS_CLOSE, 1)

    if desc is not None:
        if not _DESC_RE.search(content):
            raise ValueError("no <memory:description> element found")
        content = _DESC_RE.sub(
            lambda m: m.group(1) + escape_text(desc.strip()) + m.group(2), content, count=1)

    if reasoning is not None:
        if _REASON_CLOSE in content:
            add = "\n\n---\n" + escape_text(reasoning.strip()) + _REASON_CLOSE
            content = content.replace(_REASON_CLOSE, add, 1)
        else:
            raise ValueError("no <memory:reasoning> element found")

    for target in (uses or []):
        esc = escape_text(target)
        rel = '    <memory:relation target="%s" type="USES"/>\n  ' % esc
        if _RELS_CLOSE in content:
            # dedupe against the ESCAPED form actually present in the file, or a
            # target containing '&'/'"' is never matched and duplicates accumulate.
            if ('target="%s" type="USES"' % esc) not in content:
                content = content.replace(_RELS_CLOSE, rel + _RELS_CLOSE, 1)
        else:
            raise ValueError("no <memory:relations> block found (add one first)")

    _validate_or_rollback(filepath, content, original)
    return step_no


def _append_chain_step_v5(filepath, content, original, step_text,
                          desc=None, reasoning=None, uses=None):
    """v5 chain append: parse -> mutate -> serialize (the serializer IS the
    well-formedness guarantee; nothing to escape)."""
    from memoryschema.format_v5 import parse_v5_content, serialize_v5
    mem = parse_v5_content(content, filepath=filepath)
    if mem is None:
        raise ValueError("v5 parse failed for %s" % filepath)
    log = list(mem.get("log") or [])
    steps = [int(m) for entry in log
             for m in re.findall(r"^Step\s+(\d+)\s*:", str(entry))]
    step_no = (max(steps) if steps else len(log)) + 1
    text = step_text.strip()
    if not re.match(r"^(Step\s+\d+|Conclusion)\s*:", text, re.IGNORECASE):
        text = "Step %d: %s" % (step_no, text)
    text = " ".join(text.split())               # single-line bullet (markdown list item)
    log.append(text)
    obs_atomic = [o for o in (mem.get("observations") or []) if o not in (mem.get("log") or [])]
    mem["log"] = log
    mem["observations"] = obs_atomic + log
    if desc is not None:
        mem["summary"] = desc.strip()           # the evolving summary lives in ## Summary in v5
    if reasoning is not None:
        prev = mem.get("reasoning") or ""
        mem["reasoning"] = (prev + "\n\n---\n" + reasoning.strip()).strip()
    rels = list(mem.get("relations") or [])
    for target in (uses or []):
        if not any(r.get("target") == target and r.get("type") == "USES" for r in rels):
            rels.append({"type": "USES", "target": target})
    mem["relations"] = rels

    new_content = serialize_v5(mem)
    from memoryschema.format_v5 import parse_v5_content as _reparse
    if _reparse(new_content, filepath=filepath) is None:
        raise ValueError("v5 serialize round-trip failed — file left unchanged")
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    return step_no


def set_lifecycle(filepath, status=None, superseded_at=None, superseded_by=None,
                  valid_from=None, promoted_to=None):
    """Deterministically update LIFECYCLE frontmatter on a v5 entity .md —
    the file-first fix for the archive-reverts-on-reconcile bug: status and
    temporal fields must live in the source of truth or reconcile (which
    rebuilds the stores FROM the .md set) silently resurrects entities.

    This is metadata-only mutation (never content), performed by code — the
    lifecycle analogue of the archive/supersession machinery, exempt from the
    active-chain content-authorization model.
    """
    from memoryschema.format_v5 import is_v5_content, parse_v5_content, serialize_v5
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if not is_v5_content(content):
        raise ValueError("set_lifecycle requires a v5 entity: %s" % filepath)
    mem = parse_v5_content(content, filepath=filepath)
    if mem is None:
        raise ValueError("v5 parse failed for %s" % filepath)
    if status is not None:
        mem["status"] = status
    if superseded_at is not None:
        mem["superseded_at"] = superseded_at
    if superseded_by is not None:
        mem["superseded_by"] = superseded_by
    if valid_from is not None:
        mem["valid_from"] = valid_from
    if promoted_to is not None:
        mem["promoted_to"] = promoted_to
    new_content = serialize_v5(mem)
    if parse_v5_content(new_content, filepath=filepath) is None:
        raise ValueError("lifecycle serialize round-trip failed — file unchanged")
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_content)
    return mem


def find_active_by_key(store_path, fact_key, exclude=None):
    """Find the ACTIVE entity holding fact `key` (deterministic supersession
    lookup — no LLM judgment, exact key match only)."""
    import json as _json
    if not fact_key or not os.path.exists(store_path):
        return None
    with open(store_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = _json.loads(line)
            except Exception:
                continue
            if (e.get("key") == fact_key
                    and (e.get("status") or "active") == "active"
                    and e.get("name") != exclude):
                return e.get("name")
    return None


def create_entity_file(filepath, name, description, observations,
                       importance=None, mtype=None, reasoning=None,
                       relations=None, project=None, body=None,
                       fact_key=None, valid_from=None):
    """Generate a well-formed entity .md from plain-text parts.

    Emits v5 (YAML frontmatter + markdown body) when MEMORYSCHEMA_V5=1,
    else v4 XML (the default until the corpus migrates). relations: list of
    (TYPE, target) tuples. Refuses to overwrite an existing file.
    """
    if os.path.exists(filepath):
        raise FileExistsError("%s already exists — entities are created once" % filepath)

    if os.environ.get("MEMORYSCHEMA_V5") == "1":
        from memoryschema.format_v5 import parse_v5_content, serialize_v5
        mem = {"schema": 5, "name": name, "description": description.strip(),
               "observations": list(observations),
               "type": mtype or "semantic",
               "relations": [{"type": t, "target": tg} for t, tg in (relations or [])]}
        if importance is not None:
            mem["importance"] = int(importance)
        if reasoning:
            mem["reasoning"] = reasoning.strip()
        if project:
            mem["project"] = project
        if fact_key:
            mem["key"] = fact_key
            from datetime import date
            mem["valid_from"] = valid_from or date.today().isoformat()
        elif valid_from:
            mem["valid_from"] = valid_from
        content = serialize_v5(mem)
        if parse_v5_content(content, filepath=filepath) is None:
            raise ValueError("generated v5 entity failed to parse — refusing to write")
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        return filepath
    attrs = 'schema="4" name="%s"' % escape_text(name)
    if mtype:
        attrs += ' type="%s"' % escape_text(mtype)
    if importance is not None:
        attrs += ' importance="%d"' % int(importance)
    lines = ["<memory:entity %s>" % attrs]
    lines.append("  <memory:description>%s</memory:description>" % escape_text(description.strip()))
    lines.append("  <memory:observations>")
    for o in observations:
        lines.append("    <memory:observation>%s</memory:observation>" % escape_text(str(o).strip()))
    lines.append("  </memory:observations>")
    if reasoning:
        lines.append("  <memory:reasoning>%s</memory:reasoning>" % escape_text(reasoning.strip()))
    if relations:
        lines.append("  <memory:relations>")
        for rtype, target in relations:
            lines.append('    <memory:relation target="%s" type="%s"/>'
                         % (escape_text(target), escape_text(rtype)))
        lines.append("  </memory:relations>")
    if project:
        lines.append("  <memory:project>%s</memory:project>" % escape_text(project))
    lines.append("</memory:entity>")
    content = "\n".join(lines) + "\n"
    if body:
        content += "\n" + body.strip() + "\n"

    from memoryschema.tags import parse_memory_content
    if parse_memory_content(content) is None:
        raise ValueError("generated entity failed to parse — refusing to write")
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return filepath
