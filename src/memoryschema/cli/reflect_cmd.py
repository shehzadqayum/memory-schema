"""Reflect command — cluster episodic entries and synthesise semantic summaries."""

import json as json_mod

import click


@click.command("reflect")
@click.option("--project", "-p", default=None, help="Project scope.")
@click.option("--min-cluster", default=2, type=int, help="Minimum cluster size. Default: 2.")
@click.option("--max-cluster", default=10, type=int, help="Maximum cluster size. Default: 10.")
@click.option("--dry-run", is_flag=True, help="Preview clusters without creating summaries.")
@click.option("--include-contradictory", is_flag=True, default=False,
              help="Synthesize contradictory clusters with min importance and CONTRADICTS edges.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_obj
def reflect(config, project, min_cluster, max_cluster, dry_run, include_contradictory, as_json):
    """Cluster episodic entries and synthesise semantic summaries.

    Groups related episodic memories by association neighbourhood,
    creates a semantic summary for each cluster, and archives the
    originals with SUPERSEDES edges.

    Use --dry-run to preview clusters without creating summaries.

    Example:
        memoryschema reflect
        memoryschema reflect --project my-project --dry-run
        memoryschema reflect --min-cluster 3 --max-cluster 8
    """
    from memoryschema.consolidation import reflect as do_reflect
    from memoryschema.store import get_store

    store = get_store(config=config)
    result = do_reflect(store, project=project, min_cluster=min_cluster,
                        max_cluster=max_cluster, dry_run=dry_run,
                        include_contradictory=include_contradictory)

    if as_json:
        click.echo(json_mod.dumps(result, indent=2))
    else:
        click.echo(f"Clusters:   {result['clusters']}")
        click.echo(f"Summaries:  {result['summaries']}")
        click.echo(f"Archived:   {result['archived']}")
        click.echo(f"Skipped:    {result.get('skipped', 0)}")
        if result['dry_run']:
            click.echo("(dry run — no changes made)")
