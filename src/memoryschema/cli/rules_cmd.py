"""Rules diagnostic command — show effective rules with inheritance."""

import json as json_mod

import click


@click.command("rules")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--conflicts", is_flag=True, help="Show only rules where parent overrides child.")
@click.pass_obj
def rules(config, as_json, conflicts):
    """Show effective rules with inheritance markers.

    Displays which rules are active, where they come from,
    and which are inherited from parent agents.

    Example:
        memoryschema rules
        memoryschema rules --conflicts
        memoryschema rules --json
    """
    from memoryschema.inheritance import resolve_rules

    resolved = resolve_rules(config.project_root)

    if conflicts:
        resolved = [r for r in resolved if r['is_inherited']]

    if as_json:
        out = [{'filename': r['filename'], 'source': str(r['source_dir']),
                'is_inherited': r['is_inherited']} for r in resolved]
        click.echo(json_mod.dumps(out, indent=2))
    else:
        if not resolved:
            click.echo("No rules found.")
            return
        for r in resolved:
            marker = " [inherited]" if r['is_inherited'] else ""
            click.echo(f"  {r['filename']:40s} {r['source_dir']}{marker}")
        inherited_count = sum(1 for r in resolved if r['is_inherited'])
        if inherited_count:
            click.echo(f"\n  {inherited_count} inherited from parent agent(s)")
