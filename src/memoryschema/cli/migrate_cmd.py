"""Migration and data sync commands."""

import json
import sys

import click


@click.group()
def migrate():
    """Migrate data between JSONL and Neo4j stores.

    Commands: jsonl-to-neo4j, neo4j-to-jsonl.
    """
    pass


@migrate.command("jsonl-to-neo4j")
@click.option("--batch-size", default=500, type=int, help="Nodes per batch. Default: 500.")
@click.option("--dry-run", is_flag=True, help="Show stats without migrating.")
@click.option("--verify", "verify_flag", is_flag=True, help="Run verification after migration.")
@click.option("--skip-assoc", is_flag=True, help="Skip association migration.")
@click.pass_obj
def jsonl_to_neo4j(config, batch_size, dry_run, verify_flag, skip_assoc):
    """Migrate JSONL store to Neo4j.

    Batch-creates Memory nodes, relation edges, and optionally
    association edges from the JSONL store.

    Example:
        memoryschema migrate jsonl-to-neo4j --verify
        memoryschema migrate jsonl-to-neo4j --dry-run
    """
    from memoryschema.migration import migrate as _migrate

    result = _migrate(
        config=config,
        batch_size=batch_size,
        skip_assoc=skip_assoc,
        verify_flag=verify_flag,
        dry_run=dry_run,
    )

    click.echo(f"Entries:     {result['entries']:,}")
    click.echo(f"Embedded:    {result['embedded']:,}")
    click.echo(f"With assoc:  {result['with_assoc']:,}")
    click.echo(f"With rels:   {result['with_rels']}")

    if dry_run:
        click.echo("\n(dry run — no changes made)")
    else:
        click.echo(f"\nNodes:       {result.get('nodes_created', 0):,}")
        click.echo(f"Relations:   {result.get('relations_created', 0)}")
        click.echo(f"Associations:{result.get('associations_created', 0):,}")
        click.echo(f"Duration:    {result.get('duration_s', 0)}s")

        if result.get('verification'):
            v = result['verification']
            click.echo(f"\nVerification:")
            click.echo(f"  JSONL: {v['jsonl_count']:,}  Neo4j: {v['neo4j_count']:,}  Match: {'YES' if v['match'] else 'NO'}")


@migrate.command("neo4j-to-jsonl")
@click.option("--output", type=click.Path(), help="Output JSONL file path. Default: memory/store.jsonl.")
@click.pass_obj
def neo4j_to_jsonl(config, output):
    """Export Neo4j store to JSONL file.

    Example:
        memoryschema migrate neo4j-to-jsonl
        memoryschema migrate neo4j-to-jsonl --output backup.jsonl
    """
    output_path = output or str(config.store_path)

    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore(config=config)
        entries = store.list_all(include_inactive=True)  # include superseded/archived — JSONL is a full mirror
        store.close()
    except Exception as e:
        click.echo(f"Error: Cannot connect to Neo4j: {e}", err=True)
        click.echo("Fix: Run 'memoryschema neo4j up'.", err=True)
        sys.exit(1)

    import json as json_mod
    import os
    import tempfile
    # Guard the canonical store: Neo4j does not carry embed_input_hash / summary /
    # log / chain / confidence, so overwriting memory/store.jsonl with the Neo4j
    # projection strips those fields and forces a full re-embed on the next
    # reconcile. reconcile is the supported heal; this command is for export.
    if os.path.abspath(output_path) == os.path.abspath(str(config.store_path)):
        click.echo("Refusing to overwrite the canonical memory/store.jsonl (it carries "
                   "fields Neo4j does not). Use --output <file>, or `memoryschema "
                   "reconcile` to heal the store.", err=True)
        sys.exit(1)
    # Atomic write (tmp + os.replace) so an interrupt cannot leave a truncated file.
    dirpath = os.path.dirname(output_path) or '.'
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix='.tmp', dir=dirpath)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json_mod.dumps(entry, ensure_ascii=False) + '\n')
        os.replace(tmp, output_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    click.echo(f"Exported {len(entries):,} entries to {output_path}")


@click.command()
@click.pass_obj
def sync(config):
    """Report drift across the canonical memory/*.md set, the JSONL store, and Neo4j.

    Read-only diff over NAME-SETS + LIFECYCLE STATUSES (.md vs JSONL): counts can match
    while the sets differ, and names can match while a status drifted (an archive that
    reached only one layer). To FIX drift, run `memoryschema reconcile`.

    Example:
        memoryschema sync
    """
    from memoryschema.reconcile import diff as _diff

    d = _diff(config)
    _nc = d['neo4j_count']
    click.echo(f".md: {d['md_count']:,}    JSONL: {d['jsonl_count']:,}    "
               f"Neo4j: {('unreachable' if _nc is None else format(_nc, ','))}")
    if d.get('neo4j_error'):
        click.echo(f"  ⚠ Neo4j unreachable: {d['neo4j_error']}", err=True)
    if d.get('malformed'):
        click.echo(f"  ⚠ {len(d['malformed'])} UNPARSEABLE .md file(s) (corruption — NOT counted; "
                   f"reconcile will REFUSE until fixed): {', '.join(d['malformed'][:8])} "
                   f"— fix the XML (unescaped & / < / >) or rm the file", err=True)

    def _line(label, names):
        if names:
            more = ' …' if len(names) > 8 else ''
            click.echo(f"  {label} ({len(names)}): {', '.join(names[:8])}{more}")

    if d['in_sync']:
        click.echo("Status: in sync (name-sets + statuses match)")
        return
    click.echo("Status: OUT OF SYNC")
    _line("missing from JSONL", d['missing_from_jsonl'])
    _line("JSONL orphans (no .md)", d['jsonl_orphans'])
    _line("status drift (.md vs JSONL)", d.get('status_drift'))
    _line("Neo4j orphans (no .md)", d['neo4j_orphans'])
    click.echo("Fix: memoryschema reconcile")


@click.command()
@click.option("--dry-run", is_flag=True, help="Report the plan without writing.")
@click.option("--prune/--no-prune", default=True,
              help="Delete JSONL/Neo4j entries with no backing .md (default: prune).")
@click.option("--no-verify", "no_verify", is_flag=True, help="Skip the name-set verification pass.")
@click.option("--allow-empty", "allow_empty", is_flag=True,
              help="Bypass the safety guard that refuses to reconcile a collapsed/empty .md set.")
@click.pass_obj
def reconcile(config, dry_run, prune, no_verify, allow_empty):
    """Reconcile memory/*.md with the JSONL store and the Neo4j projection.

    Idempotent + comprehensive: reuses JSONL embeddings where the content is unchanged,
    re-embeds ALL spaces for new/changed entities, rewrites store.jsonl to EXACTLY the
    .md set, pushes it into Neo4j, PRUNES residuals with no .md, and verifies by
    name-set. A second run on a clean store is a no-op.

    Example:
        memoryschema reconcile --dry-run     # preview the plan
        memoryschema reconcile               # fix (prune + verify)
        memoryschema reconcile --no-prune    # add/update only, keep orphans
    """
    from memoryschema.reconcile import reconcile as _reconcile

    r = _reconcile(config, dry_run=dry_run, prune=prune, verify=not no_verify, allow_empty=allow_empty)
    if r.get('aborted'):
        click.echo(f"ABORTED: {r['aborted']}", err=True)
        sys.exit(1)
    _nc = r['neo4j_count']
    click.echo(f".md: {r['md_count']:,}    JSONL: {r['jsonl_count']:,}    "
               f"Neo4j: {('unreachable' if _nc is None else format(_nc, ','))}")
    if r.get('neo4j_error'):
        click.echo(f"  ⚠ Neo4j unreachable: {r['neo4j_error']}", err=True)
    if r.get('malformed'):    # dry-run reaches here with malformed set (a real run aborts above)
        click.echo(f"  ⚠ {len(r['malformed'])} UNPARSEABLE .md file(s) (corruption): "
                   f"{', '.join(r['malformed'][:8])} — fix before a real reconcile", err=True)

    def _line(label, names):
        if names:
            more = ' …' if len(names) > 6 else ''
            click.echo(f"  {label} ({len(names)}): {', '.join(names[:6])}{more}")

    _line("missing from JSONL", r['missing_from_jsonl'])
    _line("JSONL orphans", r['jsonl_orphans'])
    _line("Neo4j orphans", r['neo4j_orphans'])

    if dry_run:
        click.echo(f"\nWould re-embed: {r.get('would_reembed', 0)}   (dry run — no changes made)")
        return

    click.echo(f"Re-embedded: {r['reembedded']:,}    JSONL pruned: {r['jsonl_pruned']:,}    "
               f"Neo4j pruned: {r['neo4j_pruned']:,}")
    if r['embed_failed']:
        click.echo(f"  ⚠ {r['embed_failed']} entitie(s) not embedded (Voyage unavailable or no text)", err=True)
        for nm, msg in (r.get('embed_errors') or [])[:3]:
            click.echo(f"      - {nm}: {msg}", err=True)
    if r['neo4j_pushed']:
        msg = "Neo4j updated"
        if r.get('associations_recomputed'):
            msg += " + associations recomputed"
        click.echo(msg + ".")
        if r.get('assoc_error'):
            click.echo(f"  ⚠ associations not recomputed: {r['assoc_error']}", err=True)
    elif r.get('neo4j_push_error'):
        click.echo(f"  ⚠ Neo4j not updated: {r['neo4j_push_error']}", err=True)

    if r.get('l0_kept') is not None:
        msg = f"L0 index: {r['l0_kept']} active entities written to MEMORY.md"
        if r.get('l0_dropped'):
            msg += f" ({len(r['l0_dropped'])} lowest-importance dropped for the token budget)"
        click.echo(msg)
    elif r.get('l0_error'):
        click.echo(f"  ⚠ L0 index (MEMORY.md) not rebuilt: {r['l0_error']}", err=True)

    if 'verify_ok' in r:
        ok = r['verify_ok']
        click.echo(f"\nVerify: {'PASS — .md / JSONL / Neo4j name-sets match' if ok else 'FAIL'}")
        if not ok:
            if r.get('verify_missing'):
                click.echo(f"  missing: {', '.join(r['verify_missing'][:8])}", err=True)
            if r.get('verify_extra'):
                click.echo(f"  extra:   {', '.join(r['verify_extra'][:8])}", err=True)
            sys.exit(1)
