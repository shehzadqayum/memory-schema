"""Config diagnostic command — show effective config with inheritance chain."""

import json as json_mod

import click


@click.command("config")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--chain", "show_chain", is_flag=True, help="Show config source chain.")
@click.pass_obj
def config_cmd(config, as_json, show_chain):
    """Show effective config with inheritance chain.

    Displays the resolved configuration values and their sources.

    Example:
        memoryschema config
        memoryschema config --chain
        memoryschema config --json
    """
    from memoryschema.inheritance import walk_config_chain, load_toml_config, flatten_toml

    if show_chain:
        chain = walk_config_chain(config.project_root)
        if as_json:
            out = [{'path': str(p), 'values': flatten_toml(load_toml_config(p))}
                   for p in chain]
            click.echo(json_mod.dumps(out, indent=2))
        else:
            if not chain:
                click.echo("No memoryschema.toml files found in chain.")
                return
            for i, path in enumerate(chain):
                role = "child" if i == 0 else f"ancestor ({i} levels up)"
                values = flatten_toml(load_toml_config(path))
                click.echo(f"  [{role}] {path}")
                for k, v in sorted(values.items()):
                    click.echo(f"    {k}: {v}")
    else:
        info = {
            'project_name': config.project_name,
            'project_root': str(config.project_root),
            'store_path': str(config.store_path),
            'neo4j_uri': config.neo4j_uri,
            'neo4j_user': config.neo4j_user,
            'neo4j_container_name': config.neo4j_container_name,
            'voyage_api_key': f"{config.voyage_api_key[:8]}..." if config.voyage_api_key else None,
            'embed_model': config.embed_model,
            'recency_decay': config.recency_decay,
            'recall_depth': config.recall_depth,
            'recall_decay': config.recall_decay,
        }
        if as_json:
            click.echo(json_mod.dumps(info, indent=2))
        else:
            for k, v in info.items():
                click.echo(f"  {k:25s} {v}")
