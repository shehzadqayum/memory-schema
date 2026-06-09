"""Indexing and embedding commands."""

import json
import sys

import click


@click.command("index")
@click.option("--base-path", type=click.Path(exists=True),
              help="Root directory containing memory .md files. Default: memory/.")
@click.option("--project", "project_scope", help="Project name for scoping.")
@click.option("--embed", "do_embed", is_flag=True, help="Embed memories via Voyage AI.")
@click.pass_obj
def index(config, base_path, project_scope, do_embed):
    """Batch index un-indexed memory files into the store.

    Discovers .md files, parses entities, upserts to store,
    computes backlinks, and optionally embeds.

    Example:
        memoryschema index
        memoryschema index --base-path memory/tweets/ --project ict --embed
    """
    from memoryschema.consolidation import consolidate
    from memoryschema.store import get_store

    if base_path is None:
        base_path = str(config.memory_dir)
    if project_scope is None:
        project_scope = config.project_name

    store = get_store(config=config)
    result = consolidate(base_path, project_scope, store, embed=do_embed)

    click.echo(f"Indexed:      {result['synced']} files")
    click.echo(f"Skipped:      {result['skipped']} unparseable")
    click.echo(f"Backlinks:    {result['backlinks']} entries")
    if do_embed:
        click.echo(f"Embedded:     {result['embedded']} entries")
        click.echo(f"Associations: {result['associations']} entries")


@click.command("embed")
@click.option("--prefix", help="Name prefix filter (e.g., forum-, tweet-).")
@click.option("--all", "embed_all", is_flag=True, help="Re-embed all entries.")
@click.option("--coverage", is_flag=True, help="Show embedding coverage stats only.")
@click.option("--batch-size", default=20, type=int, help="Embedding batch size. Default: 20.")
@click.option("--dry-run", is_flag=True, help="Show stats without re-embedding.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_obj
def embed(config, prefix, embed_all, coverage, batch_size, dry_run, as_json):
    """Re-embed entries by prefix or all.

    Example:
        memoryschema embed --prefix forum- --batch-size 50
        memoryschema embed --all --dry-run
        memoryschema embed --coverage
    """
    if coverage:
        store = _get_store(config)
        entries = store.list_all()
        total = len(entries)
        embedded = sum(1 for e in entries if e.get('embedding'))
        pct = (embedded / total * 100) if total > 0 else 0
        if as_json:
            click.echo(json.dumps({"total": total, "embedded": embedded, "coverage_pct": round(pct, 1)}))
        else:
            click.echo(f"Total:    {total:,}")
            click.echo(f"Embedded: {embedded:,}")
            click.echo(f"Coverage: {pct:.1f}%")
        return

    if not prefix and not embed_all:
        click.echo("Error: Specify --prefix or --all.", err=True)
        sys.exit(1)

    if embed_all:
        prefix = ""

    from memoryschema.reembed import reembed
    result = reembed(prefix=prefix, config=config, batch_size=batch_size, dry_run=dry_run)

    if as_json:
        click.echo(json.dumps(result))
    else:
        click.echo(f"Total:        {result['total']:,}")
        click.echo(f"Matched:      {result['matched']:,}")
        click.echo(f"Embedded:     {result['embedded']:,}")
        if result.get('associations'):
            click.echo(f"Associations: {result['associations']:,}")
        if result.get('dry_run'):
            click.echo("(dry run — no changes made)")


@click.command()
@click.option("--recompute", is_flag=True, help="Recompute all k-NN associations.")
@click.option("--k", default=10, type=int, help="Number of nearest neighbors. Default: 10.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_obj
def associations(config, recompute, k, as_json):
    """Show or recompute k-NN associations.

    Without --recompute, shows current association stats.
    With --recompute, recomputes all associations (may take minutes for large stores).

    Example:
        memoryschema associations
        memoryschema associations --recompute --k 10
    """
    store = _get_store(config)

    if recompute:
        click.echo(f"Computing k={k} nearest neighbors...")
        count = store.compute_associations(k=k)
        click.echo(f"Computed associations for {count:,} entries.")
    else:
        entries = store.list_all()
        with_assoc = sum(1 for e in entries if e.get('associations'))
        total_edges = sum(len(e.get('associations', [])) for e in entries)
        if as_json:
            click.echo(json.dumps({"with_associations": with_assoc, "total_edges": total_edges}))
        else:
            click.echo(f"Entries with associations: {with_assoc:,}")
            click.echo(f"Total association edges:   {total_edges:,}")


def _get_store(config):
    from memoryschema.store import get_store
    return get_store(config=config)
