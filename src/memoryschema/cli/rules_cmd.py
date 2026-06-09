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
    from memoryschema.inheritance import resolve_rules, overridden_rules

    resolved = resolve_rules(config.project_root)
    overridden = overridden_rules(config.project_root)
    overridden_names = {o['filename'] for o in overridden}

    if conflicts:
        if as_json:
            out = [{'filename': o['filename'],
                    'child': str(o['child_path']),
                    'parent': str(o['parent_path'])} for o in overridden]
            click.echo(json_mod.dumps(out, indent=2))
        else:
            if not overridden:
                click.echo("No conflicts — no child rules overridden by parent.")
                return
            click.echo("Overridden rules (child's version replaced by parent):")
            for o in overridden:
                click.echo(f"  {o['filename']}")
                click.echo(f"    child:  {o['child_path']}")
                click.echo(f"    parent: {o['parent_path']} [WINS]")
        return

    if as_json:
        out = [{'filename': r['filename'], 'source': str(r['source_dir']),
                'is_inherited': r['is_inherited'],
                'overrides_child': r['filename'] in overridden_names}
               for r in resolved]
        click.echo(json_mod.dumps(out, indent=2))
    else:
        if not resolved:
            click.echo("No rules found.")
            return
        for r in resolved:
            if r['filename'] in overridden_names:
                marker = " [OVERRIDDEN]"
            elif r['is_inherited']:
                marker = " [inherited]"
            else:
                marker = ""
            click.echo(f"  {r['filename']:40s} {r['source_dir']}{marker}")
        if overridden:
            click.echo(f"\n  {len(overridden)} child rule(s) overridden by parent. "
                       f"Use --conflicts for details.")
