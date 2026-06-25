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
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json_mod.dumps(entry, ensure_ascii=False) + '\n')

    click.echo(f"Exported {len(entries):,} entries to {output_path}")


@click.command()
@click.pass_obj
def sync(config):
    """Reconcile JSONL and Neo4j stores.

    Compares entry counts and reports differences.

    Example:
        memoryschema sync
    """
    from memoryschema.store import MemoryStore

    jsonl_store = MemoryStore(str(config.store_path))
    jsonl_count = jsonl_store.count()

    neo4j_count = 0
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        neo4j_store = Neo4jMemoryStore(config=config)
        neo4j_count = neo4j_store.count()
        neo4j_store.close()
    except Exception:
        click.echo("Warning: Neo4j not available.", err=True)

    click.echo(f"JSONL: {jsonl_count:,} entries")
    click.echo(f"Neo4j: {neo4j_count:,} nodes")
    if jsonl_count == neo4j_count:
        click.echo("Status: in sync")
    else:
        diff = abs(jsonl_count - neo4j_count)
        click.echo(f"Status: out of sync ({diff:,} difference)")
        if jsonl_count > neo4j_count:
            click.echo("Fix: Run 'memoryschema migrate jsonl-to-neo4j'")
        else:
            click.echo("Fix: Run 'memoryschema migrate neo4j-to-jsonl'")
