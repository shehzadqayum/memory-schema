"""Memory store operations — day-to-day management."""

import json
import sys

import click


def _get_store(config):
    """Get best available store backend."""
    from memoryschema.store import get_store
    return get_store(config=config)


def _remove_from_memory_index(config, name):
    """Remove an entry from the MEMORY.md index."""
    index_path = config.memory_index_path
    if index_path.exists():
        lines = index_path.read_text().split('\n')
        new_lines = [l for l in lines if f'[{name}]' not in l]
        if len(new_lines) != len(lines):
            index_path.write_text('\n'.join(new_lines))
            return True
    return False


@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def status(config, as_json):
    """Show store backend, node count, embedding coverage, association density.

    Example:
        memoryschema status
        memoryschema status --json
    """
    store = _get_store(config)
    backend = type(store).__name__
    count = store.count()

    info = {"backend": backend, "nodes": count}

    if as_json:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"Backend: {backend}")
        click.echo(f"Nodes:   {count:,}")
        click.echo(f"Store:   {config.store_path}")
        click.echo(f"URI:     {config.neo4j_uri}")


@click.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, type=int, help="Maximum results. Default: 10.")
@click.option("--project", "-p", default=None, help="Scope recall to this project hierarchy.")
@click.option("--include-inactive", is_flag=True, default=False,
              help="Include archived/superseded/quarantined entries.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.option("--as-of", "as_of", default=None,
              help="Point-in-time recall (ISO date): facts valid AT that date, "
                   "including since-superseded ones (valid_from <= date < superseded_at).")
@click.pass_obj
def recall(config, query, limit, project, include_inactive, as_of, as_json):
    """Semantic search across memories.

    Finds seed memories via vector similarity, then cascades through
    relations, backlinks, and associations.

    Use --project to scope recall to a project and its hierarchy
    (parent sees children, children inherit from parent).

    Example:
        memoryschema recall "order block definition"
        memoryschema recall "schema v2 changes" --limit 5
        memoryschema recall "auth flow" --project ict.auth
    """
    store = _get_store(config)
    results = store.recall(
        query=query, limit=limit if not as_of else max(limit * 4, 20), project=project,
        include_inactive=include_inactive or bool(as_of),
        depth=config.recall_depth, decay=config.recall_decay,
        max_inherit_depth=config.max_inherit_depth,
    )
    if as_of:
        # Temporal filter: keep entries valid AT the date — valid_from <= as_of and
        # not yet superseded then. Recall results are a projected subset without
        # temporal fields, so enrich from the JSONL metadata (the same local source
        # find_active_by_key uses — backend-independent). Fallback: created_at.
        import json as _json
        meta = {}
        try:
            with open(str(config.store_path), "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line:
                        continue
                    try:
                        _e = _json.loads(_line)
                        meta[_e.get("name")] = _e
                    except Exception:
                        continue
        except OSError:
            pass
        def _valid_at(r):
            e = meta.get(r.get("name"), r)
            if (e.get("status") or "active") not in ("active", "superseded"):
                return False
            vf = e.get("valid_from") or (e.get("created_at") or "")[:10]
            sa = e.get("superseded_at")
            if vf and vf > as_of:
                return False
            if sa and sa <= as_of:
                return False
            return True
        results = [r for r in results if _valid_at(r)][:limit]

    # Annotate staleness for entries with verified_at
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    staleness_days = getattr(config, 'verification_staleness_days', 7)
    for r in results:
        va = r.get('verified_at')
        if va:
            try:
                vt = datetime.fromisoformat(va)
                if vt.tzinfo is None:
                    vt = vt.replace(tzinfo=timezone.utc)
                age_hours = max(0, (now - vt).total_seconds() / 3600)
                r['verification_age_hours'] = round(age_hours, 1)
            except (ValueError, TypeError):
                pass

    # Decensoring probe (opt-in retrieval.probe_slot): APPEND one dormant entity, marked
    # channel='probe' — a cited probe is decensored evidence of knowledge suppression.
    if getattr(config, "probe_slot", False) and not as_of:
        from memoryschema.recall_log import pick_probe
        _probe = pick_probe(config, store, {r.get("name") for r in results})
        if _probe:
            results = list(results) + [_probe]

    # Telemetry: record that this recall happened (Move 1 — measure whether memory is read).
    # Best-effort + separate from scoring; never breaks recall.
    from memoryschema.recall_log import log_recall
    backend = type(store).__name__
    log_recall(config, query, results, backend=backend, degraded=(backend != "Neo4jMemoryStore"))

    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        if not results:
            click.echo("No results found.")
            return
        for r in results:
            untrusted = r.get('untrusted') or r.get('provenance') == 'ingested'
            prefix = "  "
            if untrusted:
                prefix = "! "
            click.echo(f"{prefix}{r['score']:.3f} [{r['channel']}] {r['name']}")
            if untrusted:
                click.echo(f"         [UNTRUSTED — ingested, provenance unverified]")
            # Staleness annotation (v4)
            age_hours = r.get('verification_age_hours')
            if age_hours is not None:
                age_days = age_hours / 24
                if age_days > staleness_days:
                    click.echo(f"         [VERIFICATION STALE: {int(age_days)}d]")
                else:
                    click.echo(f"         [VERIFIED {int(age_days)}d ago]")
            if r.get('description'):
                click.echo(f"         {r['description'][:100]}")


@click.command("recall-stats")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--strong", default=0.5, type=float, help="Top-score threshold for a 'strong' hit.")
@click.pass_obj
def recall_stats(config, as_json, strong):
    """Summarise recall usage from the telemetry log — is memory actually being READ?

    Reports recall frequency, strong-hit rate, most-surfaced memories, and never-surfaced
    (dead-weight) entities. Populated by `memoryschema recall`. (Move 1 of the value-measurement plan.)
    """
    from memoryschema.recall_log import compute_stats
    store = _get_store(config)
    known = {e.get("name") for e in store.list_all(include_inactive=True)}
    s = compute_stats(config, strong=strong, known_names=known)
    if as_json:
        click.echo(json.dumps(s, indent=2))
        return
    if not s["events"]:
        click.echo("No recall events logged yet — run `memoryschema recall` a few times, then re-check.")
        return
    click.echo(f"Recall events:        {s['events']}  (over {s['distinct_days']} day(s), ~{s['recalls_per_day']}/day)")
    click.echo(f"Returned results:     {s['with_results']}")
    click.echo(f"Strong hits (>={strong}):  {s['strong_hits']}  ({s['strong_hit_rate']:.0%})")
    click.echo(f"Degraded recalls:     {s['degraded']}")
    click.echo(f"Never-surfaced:       {s.get('never_surfaced_count','?')} of {len(known)} entities (dead-weight candidates)")
    if s["top_surfaced"]:
        click.echo("Most-surfaced memories:")
        for name, c in s["top_surfaced"]:
            click.echo(f"  {c:3d}  {name}")


@click.command()
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def get(config, name, as_json):
    """Retrieve a single entity by name.

    Example:
        memoryschema get my-memory-name
    """
    store = _get_store(config)
    entry = store.get(name)

    if entry is None:
        click.echo(f"Error: Entity '{name}' not found.", err=True)
        sys.exit(1)

    if as_json:
        # Remove embedding for readability
        output = {k: v for k, v in entry.items() if k != 'embedding'}
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"Name:        {entry.get('name')}")
        click.echo(f"Description: {entry.get('description')}")
        click.echo(f"Type:        {entry.get('type', 'semantic')}")
        click.echo(f"Importance:  {entry.get('importance', 5)}")
        if entry.get('observations'):
            click.echo(f"Observations ({len(entry['observations'])}):")
            for obs in entry['observations'][:5]:
                click.echo(f"  - {obs[:120]}")
        if entry.get('prompt'):
            click.echo(f"Prompt:      {entry['prompt'][:120]}")
        if entry.get('reasoning'):
            click.echo(f"Reasoning:   {entry['reasoning'][:200]}")
        if entry.get('relations'):
            click.echo(f"Relations ({len(entry['relations'])}):")
            for r in entry['relations']:
                click.echo(f"  -{r.get('type')}-> {r.get('target')}")
        if entry.get('backlinks'):
            click.echo(f"Backlinks ({len(entry['backlinks'])}):")
            for b in entry['backlinks']:
                click.echo(f"  <-{b.get('type')}- {b.get('source')}")
        if entry.get('associations'):
            click.echo(f"Associations ({len(entry['associations'])}):")
            for a in entry['associations'][:10]:
                score = a.get('score')
                score_str = f" ({score:.3f})" if isinstance(score, (int, float)) else ""
                click.echo(f"  ~ {a.get('name')}{score_str}")


@click.command("list")
@click.option("--type", "type_filter", help="Filter by type: semantic, episodic, procedural.")
@click.option("--project", "project_filter", help="Filter by project name.")
@click.option("--limit", "-n", default=20, type=int, help="Maximum results. Default: 20.")
@click.option("--include-inactive", is_flag=True, default=False,
              help="Include archived/superseded/quarantined entries.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def list_cmd(config, type_filter, project_filter, limit, include_inactive, as_json):
    """List entities with optional filters.

    Example:
        memoryschema list --type semantic --limit 10
        memoryschema list --project my-project
    """
    store = _get_store(config)
    results = store.search(type=type_filter, project=project_filter, limit=limit,
                           include_inactive=include_inactive)

    if as_json:
        click.echo(json.dumps([{k: v for k, v in r.items() if k != 'embedding'} for r in results], indent=2))
    else:
        click.echo(f"Showing {len(results)} entities:")
        for r in results:
            imp = r.get('importance', 5) or 5
            click.echo(f"  [{imp:2d}] {r.get('name', '?'):40s} {r.get('description', '')[:60]}")


@click.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_obj
def write(config, file_path):
    """Parse, validate, gate-check, embed, and index a single memory file.

    Pipeline: parse → validate → write gate → embed (if accepted) → index.
    Gate verdicts: ACCEPT (normal), REJECT (exit 1), QUARANTINE (saved unembedded).

    Example:
        memoryschema write memory/my-memory.md
    """
    from memoryschema.tags import parse_memory_file
    from memoryschema.validator import validate

    # Parse
    memory = parse_memory_file(file_path)
    if memory is None:
        click.echo(f"Error: Failed to parse {file_path}.", err=True)
        sys.exit(1)

    # Validate
    with open(file_path) as f:
        content = f.read()
    errors = validate(content, file_path)
    if errors:
        click.echo(f"Validation errors in {file_path}:")
        for rule, msg in errors:
            click.echo(f"  [{rule}] {msg}")
        sys.exit(1)

    # Generator stamp (v4)
    if config.generator_id:
        memory['generator'] = config.generator_id

    # Embed BEFORE gate (stages 4-6 need the embedding vector).
    # `write` is an explicit MATERIALIZE command — hard-require Neo4j by default (like `index`) so a
    # missing backend fails loud instead of writing JSONL-only that drifts.
    from memoryschema.store import get_store
    try:
        store = get_store(config=config, require_neo4j=config.require_neo4j)
    except ConnectionError as e:
        raise click.ClickException(
            f"{e}\n`write` requires Neo4j by default. Run `memoryschema preflight`, or set "
            f"MEMORYSCHEMA_REQUIRE_NEO4J=false to write JSONL-only (drift heals on `reconcile`).")
    if config.voyage_api_key:
        try:
            from memoryschema.embeddings import embed_text
            from memoryschema.embedding_input import compose_embedding_text
            text = compose_embedding_text(memory)
            memory['embedding'] = embed_text(text, config=config)
            click.echo(f"Embedded: {len(memory['embedding'])} dimensions.")
        except Exception as e:
            click.echo(f"Warning: Embedding failed: {e}", err=True)

    # Write gate pipeline (all 6 stages, with store + config)
    from memoryschema.write_gate import gate_pipeline, GateVerdict
    gate_result = gate_pipeline(memory, store=store, config=config)

    # Audit log — every gate decision is recorded
    try:
        from memoryschema.audit import log_gate_decision
        audit_path = str(config.memory_dir / 'audit.jsonl')
        log_gate_decision(
            audit_path, memory.get('name', '?'),
            gate_result.verdict.value,
            gate_result.reasons + gate_result.warnings,
            provenance=memory.get('provenance'))
    except Exception:
        pass  # Audit failure must not block writes

    for w in gate_result.warnings:
        click.echo(f"Gate: {w}", err=True)

    if gate_result.verdict == GateVerdict.REJECT:
        for r in gate_result.reasons:
            click.echo(f"REJECTED: {r}", err=True)
        sys.exit(1)

    if gate_result.verdict == GateVerdict.QUARANTINE:
        for r in gate_result.reasons:
            click.echo(f"QUARANTINED: {r}", err=True)
        memory['status'] = 'quarantined'
        memory.pop('embedding', None)  # quarantined = unembedded
        store.upsert(memory)
        click.echo(f"Quarantined: {memory['name']} (review with: memoryschema quarantine review {memory['name']})")
        return

    # ACCEPT path — embed already done above, just index
    store.upsert(memory)
    click.echo(f"Indexed: {memory['name']}")


@click.command()
@click.argument("name")
@click.option("--confirm", is_flag=True, help="Required. Confirms deletion.")
@click.pass_obj
def delete(config, name, confirm):
    """Remove an entity from all stores, .md file, and MEMORY.md.

    WARNING: This permanently deletes the entity. Cleans up inbound
    relations, removes the .md file on disk, and removes the entry
    from MEMORY.md.

    Example:
        memoryschema delete my-memory --confirm
    """
    if not confirm:
        click.echo(f"This will DELETE entity '{name}' from all stores. Use --confirm to proceed.")
        sys.exit(1)

    store = _get_store(config)
    deleted = store.delete(name)

    # Delete from BOTH stores + the sidecar: get_store may have returned Neo4j,
    # leaving the JSONL entry and its .npz to resurface in degraded (JSONL) recall.
    import os
    from memoryschema.store import MemoryStore
    from memoryschema import vector_sidecar
    try:
        jsonl = MemoryStore(str(config.store_path))
        deleted = jsonl.delete(name) or deleted
    except Exception:
        pass
    npz = vector_sidecar._npz_path(vector_sidecar.sidecar_dir(str(config.store_path)), name)
    if os.path.exists(npz):
        try:
            os.unlink(npz)
        except OSError:
            pass

    if not deleted:
        click.echo(f"Error: Entity '{name}' not found.", err=True)
        sys.exit(1)

    click.echo(f"Deleted from store: {name}")

    # Remove .md file
    md_path = config.memory_dir / f"{name}.md"
    if md_path.exists():
        md_path.unlink()
        click.echo(f"Deleted file: {md_path}")

    # Remove from MEMORY.md
    index_path = config.memory_index_path
    if index_path.exists():
        lines = index_path.read_text().split('\n')
        new_lines = [l for l in lines if f'[{name}]' not in l]
        if len(new_lines) != len(lines):
            index_path.write_text('\n'.join(new_lines))
            click.echo(f"Removed from MEMORY.md")


@click.command()
@click.argument("name")
@click.pass_obj
def archive(config, name):
    """Archive a memory (set status=archived).

    Archived memories are excluded from default recall and search
    but remain in the store. Use --include-inactive to retrieve them.
    Also removes the entry from MEMORY.md.

    Example:
        memoryschema archive my-memory
    """
    store = _get_store(config)
    archived = store.archive(name)
    if archived:
        # File-first: persist status into the .md frontmatter, or the next reconcile
        # (which rebuilds the stores FROM the .md set) silently resurrects the entity
        # — the bug that reverted 7 step-72 archives.
        try:
            import os as _os
            from memoryschema.write_index import set_lifecycle
            set_lifecycle(_os.path.join(str(config.memory_dir), f"{name}.md"), status="archived")
        except (ValueError, OSError) as e:
            click.echo(f"  warn: status not persisted to .md ({e}) — will revert on reconcile", err=True)
        if _remove_from_memory_index(config, name):
            click.echo(f"Removed from MEMORY.md")
        click.echo(f"Archived: {name}")
    else:
        click.echo(f"Error: Entity '{name}' not found.", err=True)
        sys.exit(1)


@click.command()
@click.argument("name")
@click.pass_obj
def unarchive(config, name):
    """Unarchive a memory (set status back to active).

    Only works on archived entries.

    Example:
        memoryschema unarchive my-memory
    """
    store = _get_store(config)
    result = store.unarchive(name)
    if result:
        try:
            import os as _os
            from memoryschema.write_index import set_lifecycle
            set_lifecycle(_os.path.join(str(config.memory_dir), f"{name}.md"), status="active")
        except (ValueError, OSError):
            pass  # store updated; .md persistence is best-effort on unarchive
        click.echo(f"Unarchived: {name}")
    else:
        click.echo(f"Error: Entity '{name}' not found or not archived.", err=True)
        sys.exit(1)


@click.command()
@click.argument("name")
@click.pass_obj
def reactivate(config, name):
    """Reactivate a superseded memory (set status back to active).

    Only works on superseded entries.

    Example:
        memoryschema reactivate my-memory
    """
    store = _get_store(config)
    result = store.reactivate(name)
    if result:
        click.echo(f"Reactivated: {name}")
    else:
        click.echo(f"Error: Entity '{name}' not found or not superseded.", err=True)
        sys.exit(1)


@click.command()
@click.argument("text")
@click.option("--type", "type_filter", help="Filter by type.")
@click.option("--project", "-p", default=None, help="Filter to this project subtree.")
@click.option("--limit", "-n", default=10, type=int, help="Maximum results. Default: 10.")
@click.option("--include-inactive", is_flag=True, default=False,
              help="Include archived/superseded/quarantined entries.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def search(config, text, type_filter, project, limit, include_inactive, as_json):
    """Full-text keyword search (not semantic — substring match).

    Use --project to filter results to a project subtree.

    Example:
        memoryschema search "order block"
        memoryschema search "schema" --type semantic
        memoryschema search "auth" --project ict
    """
    store = _get_store(config)
    results = store.search(query=text, type=type_filter, project=project, limit=limit,
                           include_inactive=include_inactive)

    if as_json:
        click.echo(json.dumps([{k: v for k, v in r.items() if k != 'embedding'} for r in results], indent=2))
    else:
        click.echo(f"Found {len(results)} matches:")
        for r in results:
            click.echo(f"  {r.get('name', '?'):40s} {r.get('description', '')[:60]}")


# --- Quarantine ---

@click.group()
def quarantine():
    """Review quarantined memories (list, release, reject)."""
    pass


@quarantine.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_obj
def quarantine_list(config, as_json):
    """List all quarantined entries."""
    store = _get_store(config)
    results = store.list_all(include_inactive=True)
    quarantined = [e for e in results if e.get('status') == 'quarantined']

    if as_json:
        click.echo(json.dumps(
            [{k: v for k, v in e.items() if k != 'embedding'} for e in quarantined],
            indent=2))
    else:
        if not quarantined:
            click.echo("No quarantined entries.")
        else:
            click.echo(f"{len(quarantined)} quarantined:")
            for e in quarantined:
                click.echo(f"  {e.get('name', '?'):40s} {e.get('description', '')[:60]}")


@quarantine.command("review")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_obj
def quarantine_review(config, name, as_json):
    """Show full details of a quarantined entry for review.

    Displays all fields so you can decide whether to release or reject.

    Example:
        memoryschema quarantine review suspicious-entry
    """
    store = _get_store(config)
    entry = store.get(name)
    if not entry:
        click.echo(f"Error: Entity '{name}' not found.", err=True)
        sys.exit(1)
    if entry.get('status') != 'quarantined':
        click.echo(f"Note: '{name}' status is '{entry.get('status', 'active')}' (not quarantined).",
                    err=True)

    if as_json:
        output = {k: v for k, v in entry.items() if k != 'embedding'}
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"Name:        {entry.get('name')}")
        click.echo(f"Status:      {entry.get('status', 'active')}")
        click.echo(f"Provenance:  {entry.get('provenance', 'first-party')}")
        click.echo(f"Type:        {entry.get('type', 'semantic')}")
        click.echo(f"Importance:  {entry.get('importance', 5)}")
        click.echo(f"Description: {entry.get('description')}")
        if entry.get('source'):
            click.echo(f"Source:      {entry['source']}")
        if entry.get('observations'):
            click.echo(f"Observations ({len(entry['observations'])}):")
            for obs in entry['observations'][:10]:
                click.echo(f"  - {obs[:120]}")
        if entry.get('prompt'):
            click.echo(f"Prompt:      {entry['prompt'][:200]}")
        if entry.get('reasoning'):
            click.echo(f"Reasoning:   {entry['reasoning'][:200]}")
        click.echo(f"\nActions:")
        click.echo(f"  memoryschema quarantine release {name}")
        click.echo(f"  memoryschema quarantine reject {name} --confirm")


@quarantine.command("release")
@click.argument("name")
@click.pass_obj
def quarantine_release(config, name):
    """Release a quarantined memory (set status back to active)."""
    store = _get_store(config)
    result = store.release_quarantine(name)
    if result:
        click.echo(f"Released: {name}")
    else:
        click.echo(f"Error: Entity '{name}' not found or not quarantined.", err=True)
        sys.exit(1)


@quarantine.command("reject")
@click.argument("name")
@click.option("--confirm", is_flag=True, help="Required. Confirms deletion.")
@click.pass_obj
def quarantine_reject(config, name, confirm):
    """Reject and delete a quarantined memory."""
    if not confirm:
        click.echo(f"This will DELETE quarantined entity '{name}'. Use --confirm to proceed.")
        sys.exit(1)
    store = _get_store(config)
    entry = store.get(name)
    if not entry or entry.get('status') != 'quarantined':
        click.echo(f"Error: Entity '{name}' not found or not quarantined.", err=True)
        sys.exit(1)
    store.delete(name)
    # Delete from BOTH stores + the sidecar (get_store may return Neo4j, leaving the
    # JSONL row + .npz to resurface the 'rejected' entity in degraded recall).
    import os as _os
    from memoryschema.store import MemoryStore
    from memoryschema import vector_sidecar
    try:
        MemoryStore(str(config.store_path)).delete(name)
    except Exception:
        pass
    _npz = vector_sidecar._npz_path(vector_sidecar.sidecar_dir(str(config.store_path)), name)
    if _os.path.exists(_npz):
        try:
            _os.unlink(_npz)
        except OSError:
            pass
    _remove_from_memory_index(config, name)
    md_path = config.memory_dir / f"{name}.md"
    if md_path.exists():
        md_path.unlink()
    click.echo(f"Rejected and deleted: {name}")


# --- Force record ---

@click.command("force")
@click.option("--type", "force_type", required=True,
              type=click.Choice(['world-change', 'contradiction', 'supersession']),
              help="Type of force event.")
@click.option("--target", required=True, help="Target entity name.")
@click.option("--level", default="entry",
              type=click.Choice(['entry', 'cluster', 'project']),
              help="Scope level. Default: entry.")
@click.pass_obj
def force_cmd(config, force_type, target, level):
    """Record a typed force event in the audit trail.

    Used to record world-change events that have no reconstructable trace.
    Contradiction and supersession forces are normally emitted automatically;
    this command is primarily for world-change.

    Example:
        memoryschema force --type world-change --target my-entity
    """
    from memoryschema.audit import log_force
    audit_path = str(config.memory_dir / 'audit.jsonl')
    log_force(audit_path, force_type, target, level=level)
    click.echo(f"Force recorded: {force_type} → {target} (level: {level})")


# --- Decline ---

@click.command("decline")
@click.option("--reason", required=True, help="Why the write was declined.")
@click.option("--name-hint", default=None, help="Name the candidate would have had.")
@click.pass_obj
def decline_cmd(config, reason, name_hint):
    """Record a write decline — a deliberate decision not to write a memory candidate.

    Deliberately frictionless: one command, no file, no confirmation.
    Instruments only considered candidates; candidates never considered
    are invisible by construction.

    Example:
        memoryschema decline --reason "mechanical test output, no novel fact"
        memoryschema decline --reason "duplicate of existing entry" --name-hint session-state
    """
    from memoryschema.audit import log_decline
    audit_path = str(config.memory_dir / 'audit.jsonl')
    log_decline(audit_path, name_hint=name_hint, reason=reason)
    click.echo(f"Decline recorded: {reason}")


@click.command("remember")
@click.argument("name")
@click.option("--desc", required=True, help="One-line description (aim <=120 chars).")
@click.option("--obs", multiple=True, required=True,
              help="An atomic observation (repeatable). Plain text — escaping is automatic.")
@click.option("--type", "mtype", default="semantic",
              type=click.Choice(["semantic", "episodic", "procedural"]),
              help="Memory type (default semantic).")
@click.option("--importance", default=None, type=click.IntRange(1, 10),
              help="Salience 1-10 (omit for default).")
@click.option("--reasoning", default=None, help="Narrative reasoning (optional).")
@click.option("--uses", multiple=True, help="USES relation target (repeatable).")
@click.option("--informs", multiple=True, help="INFORMS relation target (repeatable).")
@click.option("--supersedes", multiple=True, help="SUPERSEDES relation target (repeatable).")
@click.option("--body", default=None, help="Markdown body after the entity block.")
@click.option("--key", "fact_key", default=None,
              help="Fact identity (e.g. config.timeout): an ACTIVE memory holding the same key "
                   "is deterministically superseded — bi-temporal, non-lossy, no LLM judgment.")
@click.option("--valid-from", default=None, help="Validity start (ISO date; default today when --key given).")
@click.option("--no-index", is_flag=True, help="Write the file only; skip indexing.")
@click.pass_obj
def remember_cmd(config, name, desc, obs, mtype, importance, reasoning,
                 uses, informs, supersedes, body, fact_key, valid_from, no_index):
    """Create a NEW standalone memory — plain text in, valid entity out.

    The deterministic standalone-write path: code generates the entity file
    (XML escaping automatic — raw '<'/'&' in prose are safe), validates it
    parses, then runs the full index pipeline (embed, gate, Neo4j+JSONL
    dual-write, L0 rebuild). Refuses to overwrite an existing entity.

    Example:
        memoryschema remember api-timeout-fix \
            --desc "Data-source reads must use a 5s timeout (hangs observed)" \
            --obs "the upstream call hangs when a modal dialog is open" \
            --obs "5s timeout + one retry resolves it" \
            --uses data-source-client --importance 7
    """
    from memoryschema.write_index import (create_entity_file, find_active_by_key,
                                          index_memory, set_lifecycle)

    project_root = str(config.project_root) if config and config.project_root else '.'
    import os
    filepath = os.path.join(project_root, "memory", f"{name}.md")
    store_path = os.path.join(project_root, "memory", "store.jsonl")

    # Deterministic write-time supersession (plan-memory-direction-2026): an ACTIVE
    # entity holding the same fact key is invalidated by this write — bi-temporal
    # (interval closed, nothing deleted), keyed exact-match only, no LLM judgment.
    old_holder = find_active_by_key(store_path, fact_key, exclude=name) if fact_key else None

    relations = ([("USES", t) for t in uses]
                 + [("INFORMS", t) for t in informs]
                 + [("SUPERSEDES", t) for t in supersedes]
                 + ([("SUPERSEDES", old_holder)] if old_holder else []))
    try:
        create_entity_file(filepath, name, desc, list(obs),
                           importance=importance, mtype=mtype, reasoning=reasoning,
                           relations=relations or None,
                           project=getattr(config, "project_name", None), body=body,
                           fact_key=fact_key, valid_from=valid_from)
    except (FileExistsError, ValueError, OSError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    _cites = list(uses) + list(informs)
    if _cites:
        from memoryschema.attribution import log_citation
        log_citation(config, source=name, targets=_cites, context="remember")
    click.echo(f"Created: memory/{name}.md ({len(obs)} observation(s))"
               + (f" · key={fact_key}" if fact_key else ""))

    # Index the NEW entity FIRST, then retire the prior holder(s) only if it landed
    # cleanly. Superseding before indexing meant a gate QUARANTINE or index failure
    # of the new entity would retire the old fact and leave the key with NO active
    # holder (the durable fact silently vanishing from recall).
    res = None
    if not no_index:
        res = index_memory(filepath, config=config)
        _probe = [w for w in res.warnings if '[numeric-probe-hit]' in str(w)]
        _other = [w for w in res.warnings if '[numeric-probe-hit]' not in str(w)]
        for w in _other[:5]:
            click.echo(f"  warn: {w}", err=True)
        if len(_other) > 5:
            click.echo(f"  warn: (+{len(_other)-5} more)", err=True)
        if _probe:  # the v4 numeric probe is noisy on number-dense chain prose — summarize
            click.echo(f"  warn: numeric-probe: {len(_probe)} cross-entity number mismatches (advisory)", err=True)
        click.echo(f"  {res.summary()}")

    # Persist supersession FILE-FIRST (keyed auto-supersession AND explicit
    # --supersedes): the store-side status flip alone reverts on reconcile.
    # Gate on the new entity being ACTIVE — a gate QUARANTINE returns res.ok=True
    # (the entry is still saved, just inactive), so retiring the old holder here
    # would strand the fact key with no ACTIVE holder.
    _new_active = res is None or (res.ok and res.verdict not in ("quarantine", "reject"))
    _to_supersede = ([old_holder] if old_holder else []) + [t for t in supersedes if t != old_holder]
    if _to_supersede and not _new_active:
        click.echo(f"  warn: new entity not active ({res.verdict}) — left "
                   f"{', '.join(_to_supersede)} ACTIVE (not superseded)", err=True)
    elif _to_supersede:
        from datetime import date
        for _old in _to_supersede:
            old_path = os.path.join(project_root, "memory", f"{_old}.md")
            if not os.path.exists(old_path):
                click.echo(f"  warn: supersede target {_old} has no .md file", err=True)
                continue
            try:
                set_lifecycle(old_path, status="superseded",
                              superseded_at=date.today().isoformat(), superseded_by=name)
                res_old = index_memory(old_path, config=config, require_active_chain_auth=False)
                _sup_note = "re-indexed" if res_old.ok else "REINDEX FAILED: " + "; ".join(res_old.errors)
                _why = f"key={fact_key}" if _old == old_holder else "explicit"
                click.echo(f"  superseded: {_old} ({_why}) — {_sup_note}")
            except (ValueError, OSError) as e:
                click.echo(f"  warn: could not supersede {_old}: {e}", err=True)

    if res is not None and not res.ok:
        raise SystemExit(1)


@click.command("dream")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable report.")
@click.pass_obj
def dream_cmd(config, as_json):
    """Dream-pass candidate report (read-only) — the discovery half of the
    consolidation loop.

    Lists released-undistilled chains, the oversized active chain, stale keyed
    facts, never-surfaced entities, and near-duplicate pairs. The dream SESSION
    (the /dream-pass skill) supplies judgment and acts via the safe primitives
    (remember / --supersedes / archive). This command never writes.
    """
    from memoryschema.chain_state import get_active_chain
    from memoryschema.dream_report import build_report

    project_root = str(config.project_root) if config and config.project_root else '.'
    active_chain = get_active_chain(project_root)
    report = build_report(config, active_chain=active_chain)

    if as_json:
        import json as _json
        click.echo(_json.dumps(report, indent=1))
        return

    click.echo("Dream-pass candidates (%s)" % report["generated"])
    click.echo("=" * 50)
    counts = report["counts"]
    total = sum(counts.values())
    if total == 0:
        click.echo("Store is consolidated — nothing to dream about.")
        return
    for section, title in (("chains", "Released chains to distill"),
                           ("oversized", "Active chain past rotation threshold"),
                           ("stale_keyed", "Stale keyed facts (review validity)"),
                           ("never_surfaced", "Never surfaced (archival candidates)"),
                           ("duplicates", "Near-duplicate pairs (merge candidates)"),
                           ("attribution_review", "Recalled but never cited (noise vs ambient)"),
                           ("promotion_candidates", "Promotion candidates (rule-like knowledge)")):
        items = report.get(section, [])
        if not items:
            continue
        click.echo("")
        click.echo("%s (%d):" % (title, len(items)))
        for it in items:
            if section == "duplicates":
                click.echo("  %.3f  %s <-> %s" % (it["cosine"], it["a"], it["b"]))
            elif section == "stale_keyed":
                click.echo("  %3dd  %s  (key=%s, since %s)"
                           % (it["age_days"], it["name"], it["key"], it["valid_from"]))
            elif section in ("chains", "oversized"):
                click.echo("  %4d obs  %s" % (it["observations"], it["name"]))
            elif section == "attribution_review":
                click.echo("  %s (%d recalls, 0 citations)" % (it["name"], it["recalls"]))
            elif section == "promotion_candidates":
                click.echo("  %s (type=%s, %d citations)"
                           % (it["name"], it.get("type") or "semantic", it["citations"]))
            else:
                click.echo("  %s — %s" % (it["name"], it.get("description", "")[:70]))
    click.echo("")
    click.echo("Act via: the /dream-pass skill (judgment + safe primitives).")


@click.command("attribution")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.option("--windows", default="24,72,168",
              help="Comma-separated hours for the aggregate attribution rate (default 24,72,168 = 1d/3d/7d). "
                   "Report multiple so a conclusion doesn't hinge on the 24h join window.")
@click.option("--alarm-drop", "alarm_drop", default=0.15, show_default=True,
              help="Drift alarm: relative fall in the trailing-14d event-level rate vs the prior 14d that "
                   "triggers a ⚠ (a guardrail to INVESTIGATE before tuning — never an auto-tune trigger).")
@click.pass_obj
def attribution_cmd(config, as_json, windows, alarm_drop):
    """Attribution report: which recalled memories actually influence work.

    Joins the recall log against the citation log (chain step --uses /
    remember --uses|--informs log at the moment they happen). A recalled-
    then-cited memory has PROVEN utility; recalled-never-cited is retrieval
    noise or ambient value. Feeds the dream pass + importance decisions.

    The aggregate block + drift alarm are the calibration GUARDRAIL (§7.3):
    a health number to watch, never a loss function to optimize (attribution
    is censored implicit feedback + Goodhart-vulnerable).
    """
    from memoryschema.attribution import compute_attribution, compute_aggregate, attribution_drift
    try:
        wins = tuple(int(w) for w in str(windows).split(",") if w.strip())
    except ValueError:
        wins = (24, 72, 168)
    rep = compute_attribution(config)
    agg = compute_aggregate(config, windows=wins or (24, 72, 168))
    drift = attribution_drift(config, window_hours=(wins[0] if wins else 24))
    rep["aggregate"] = agg
    rep["drift"] = drift
    # Drift alarm to stderr so it surfaces in both human and --json runs (never raises).
    if drift.get("rel_drop") is not None and drift["rel_drop"] > alarm_drop:
        click.echo("⚠ attribution drift: %dd rate %s → %s (rel drop %d%%) — investigate before tuning "
                   "(§7.3; do NOT auto-tune)" % (drift["period_days"], drift["prior"], drift["recent"],
                   round(100 * drift["rel_drop"])), err=True)
    if as_json:
        import json as _json
        click.echo(_json.dumps(rep, indent=1))
        return
    mems = rep["memories"]
    if not mems:
        click.echo("No recall/citation telemetry yet.")
        return
    click.echo("Attribution (recall x citation join)")
    click.echo("=" * 46)
    rows = sorted(mems.items(), key=lambda kv: -(kv[1]["recalls"] + kv[1]["citations"]))
    click.echo("%-42s %7s %6s %5s" % ("memory", "recalls", "cites", "rate"))
    for name, m in rows[:25]:
        if m["attribution_rate"] is not None:
            rate = "%d%%" % round(100 * m["attribution_rate"])
        else:
            rate = "-"
        click.echo("%-42s %7d %6d %5s" % (name[:42], m["recalls"], m["citations"], rate))
    summ = rep["summary"]
    if summ["recalled_never_cited"]:
        click.echo("")
        click.echo("Recalled >=3x, never cited (noise or ambient - dream-pass review):")
        for n in summ["recalled_never_cited"][:8]:
            click.echo("  %s (%d recalls)" % (n, mems[n]["recalls"]))
    # Aggregate guardrail (event-level rate per window) + the config regimes it segments by.
    click.echo("")
    click.echo("Aggregate event-level rate (guardrail, §7.3 — watch, do not optimize):")
    for w in agg["windows"]:
        o = agg["overall"][str(w)]
        rate = "%d%%" % round(100 * o["rate"]) if o["rate"] is not None else "-"
        click.echo("  within %4dh: %s over %d events" % (w, rate, o["events"]))
    if len(agg["by_regime"]) > 1:
        click.echo("  by config regime (%dh window):" % agg["windows"][0])
        for regime, per in sorted(agg["by_regime"].items()):
            o = per[str(agg["windows"][0])]
            rate = "%d%%" % round(100 * o["rate"]) if o["rate"] is not None else "-"
            label = "pre-cfg" if regime == "pre-cfg" else regime[:52]
            click.echo("    %s  %s (%d ev)" % (rate.rjust(4), label, o["events"]))
    if drift.get("rel_drop") is not None:
        click.echo("  drift: %dd %s → %s (rel %+d%%)" % (drift["period_days"], drift["prior"],
                   drift["recent"], round(-100 * drift["rel_drop"])))
