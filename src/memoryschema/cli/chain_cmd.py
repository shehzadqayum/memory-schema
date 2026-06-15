"""CLI commands for chain state management."""

import click


@click.group("chain")
def chain():
    """Manage the active reasoning chain."""
    pass


@chain.command("status")
@click.pass_obj
def chain_status(config):
    """Show the active chain (if any)."""
    from memoryschema.chain_state import get_active_chain
    project_root = str(config.project_root) if config and config.project_root else '.'
    active = get_active_chain(project_root)
    if active:
        click.echo(f"Active chain: {active}")
    else:
        click.echo("No active chain (all memories read-only)")


@chain.command("start")
@click.argument("name")
@click.pass_obj
def chain_start(config, name):
    """Start a new active chain (authorise it for writes)."""
    from memoryschema.chain_state import get_active_chain, set_active_chain
    project_root = str(config.project_root) if config and config.project_root else '.'
    current = get_active_chain(project_root)
    if current:
        click.echo(f"Error: chain '{current}' is already active. Release it first.", err=True)
        raise SystemExit(1)
    set_active_chain(name, project_root)
    click.echo(f"Chain started: {name} (authorised for writes)")


@chain.command("release")
@click.pass_obj
def chain_release(config):
    """Release the active chain (make it read-only permanently)."""
    from memoryschema.chain_state import release_active_chain
    project_root = str(config.project_root) if config and config.project_root else '.'
    released = release_active_chain(project_root)
    if released:
        click.echo(f"Chain released: {released} (now read-only)")
    else:
        click.echo("No active chain to release")
