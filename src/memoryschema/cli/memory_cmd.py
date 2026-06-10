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
@click.pass_obj
def recall(config, query, limit, project, include_inactive, as_json):
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
        query=query, limit=limit, project=project,
        include_inactive=include_inactive,
        max_inherit_depth=config.max_inherit_depth,
    )

    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        if not results:
            click.echo("No results found.")
            return
        for r in results:
            click.echo(f"  {r['score']:.3f} [{r['channel']}] {r['name']}")
            if r.get('description'):
                click.echo(f"         {r['description'][:100]}")


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
    """Parse, validate, embed, and index a single memory file.

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

    # Embed
    if config.voyage_api_key:
        try:
            from memoryschema.embeddings import embed_text
            parts = [memory.get('description', '')]
            parts.extend(memory.get('observations', []))
            if memory.get('prompt'):
                parts.append(memory['prompt'])
            if memory.get('reasoning'):
                parts.append(memory['reasoning'])
            memory['embedding'] = embed_text(' '.join(parts), config=config)
            click.echo(f"Embedded: {len(memory['embedding'])} dimensions.")
        except Exception as e:
            click.echo(f"Warning: Embedding failed: {e}", err=True)

    # Index
    store = _get_store(config)
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
    _remove_from_memory_index(config, name)
    md_path = config.memory_dir / f"{name}.md"
    if md_path.exists():
        md_path.unlink()
    click.echo(f"Rejected and deleted: {name}")
