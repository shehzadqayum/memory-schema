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
    """XML-escape plain text for insertion into an entity element.

    The single chokepoint that makes the M14 corruption class impossible on
    the CLI path: '<', '>', '&' in prose become entities before they ever
    touch the file.
    """
    return _xml_escape(str(text))


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

    # Stop-hook sentinel: a memory write happened this response.
    try:
        with open("/tmp/claude-memory-chain-updated", "w") as f:
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

    All text arguments are PLAIN TEXT — escaping happens here. The result is
    parse-validated; on any structural failure the file is rolled back.
    Returns the step number written.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    original = content

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
        rel = '    <memory:relation target="%s" type="USES"/>\n  ' % escape_text(target)
        if _RELS_CLOSE in content:
            if ('target="%s" type="USES"' % target) not in content:  # dedupe
                content = content.replace(_RELS_CLOSE, rel + _RELS_CLOSE, 1)
        else:
            raise ValueError("no <memory:relations> block found (add one first)")

    _validate_or_rollback(filepath, content, original)
    return step_no


def create_entity_file(filepath, name, description, observations,
                       importance=None, mtype=None, reasoning=None,
                       relations=None, project=None, body=None):
    """Generate a well-formed v4 entity .md from plain-text parts.

    relations: list of (TYPE, target) tuples. All text escaped here.
    Refuses to overwrite an existing file.
    """
    if os.path.exists(filepath):
        raise FileExistsError("%s already exists — entities are created once" % filepath)
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
