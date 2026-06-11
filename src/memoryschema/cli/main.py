"""
memoryschema CLI — unified command interface for the memory system.

Usage:
    memoryschema [--project NAME] [--root PATH] COMMAND [ARGS]

Setup & Deployment:
    init           Initialize a new project with memory system
    neo4j          Manage Neo4j Docker container (deploy, up, down, status, ...)
    voyage         Manage Voyage AI connectivity (status, test)

Memory Operations:
    status         Show store backend, node count, embedding coverage
    recall         Semantic search across memories
    get            Retrieve a single entity by name
    list           List entities with filters
    write          Parse, validate, embed, and index a memory file
    delete         Remove an entity from all stores
    search         Full-text keyword search
    archive        Set status=archived (excludes from default recall/search)
    unarchive      Restore archived memory to active
    reactivate     Restore superseded memory to active
    quarantine     Review quarantined memories (list, release, reject)

Validation & Quality:
    validate       Validate memory files against schema
    eval           Run retrieval quality evaluation (recall@k, MRR, nDCG)

Indexing & Embeddings:
    index          Batch index un-indexed files
    embed          Re-embed entries by prefix or all
    associations   Show or recompute k-NN associations
    reflect        Cluster episodic entries → semantic summaries

Migration & Data:
    migrate        Migrate between JSONL and Neo4j
    sync           Reconcile JSONL and Neo4j stores

Lifecycle:
    backup         Full or selective backup
    restore        Restore from backup archive
    reset          Wipe data (full or selective)
    clean          Complete removal of memory system from project
    export         Portable archive for moving to another project
    import         Import from portable archive

Hook Management:
    hook           Manage PostToolUse hook (install, uninstall, status, test)

Diagnostics & Inheritance:
    doctor         21-point health check (TOML, rules inheritance, tests)
    rules          Show effective rules with inheritance markers
    config         Show effective config with inheritance chain
"""

import click

from memoryschema._version import __version__
from memoryschema.config import MemoryConfig


@click.group(help=__doc__)
@click.version_option(version=__version__, prog_name="memoryschema")
@click.option(
    "--project", envvar="MEMORY_PROJECT", default="default",
    help="Project name. Used for Neo4j container naming and memory scoping. [env: MEMORY_PROJECT]",
)
@click.option(
    "--root", envvar="MEMORY_ROOT", default=".",
    type=click.Path(resolve_path=True),
    help="Project root directory. All paths are relative to this. [env: MEMORY_ROOT]",
)
@click.pass_context
def cli(ctx, project, root):
    """Memory schema system for Claude Code."""
    from memoryschema.inheritance import find_toml_config
    toml_path = find_toml_config(root)
    if toml_path is not None:
        cli_overrides = {}
        if project != "default":
            cli_overrides['project_name'] = project
        ctx.obj = MemoryConfig.from_toml(root, cli_overrides=cli_overrides or None)
    else:
        ctx.obj = MemoryConfig(project_name=project, project_root=root)


# --- Setup & Deployment ---

@cli.command()
@click.option("--with-neo4j", is_flag=True, default=False,
              help="Deploy Neo4j Docker container as part of initialization.")
@click.option("--scopes", default="working",
              help="Comma-separated scope guidelines to install: working, corpus. Default: working.")
@click.option("--neo4j-password", default=None,
              help="Neo4j password for docker-compose.yml. Random if not set.")
@click.pass_obj
def init(config, with_neo4j, scopes, neo4j_password):
    """Initialize a new project with the memory system.

    Creates memory/ directory, docker-compose.yml, .env.example,
    memoryschema.toml, and .claude/rules/ files. Optionally deploys Neo4j.

    For nested agents, run init inside the parent project. The TOML config
    supports hierarchical inheritance via dot-notation project names.

    Example:
        memoryschema init --project my-project --scopes working,corpus --with-neo4j
    """
    import os
    import secrets
    from importlib.resources import files as pkg_files

    # Generate random password if not provided
    if neo4j_password is None:
        neo4j_password = secrets.token_urlsafe(16)

    created = []

    # 1. memory/ + MEMORY.md
    config.memory_dir.mkdir(parents=True, exist_ok=True)
    index_path = config.memory_index_path
    if not index_path.exists():
        index_path.write_text("## Project Memory\n\n(entries will be added as memories are created)\n")
        created.append(str(index_path))

    # 2. docker-compose.yml
    if not config.docker_compose_path.exists():
        try:
            tpl = (pkg_files("memoryschema.templates") / "docker-compose.yml.tpl").read_text()
            content = tpl.format(
                neo4j_container_name=config.neo4j_container_name,
                neo4j_password=neo4j_password,
                neo4j_bolt_port=config.neo4j_bolt_port,
                neo4j_http_port=config.neo4j_http_port,
                volume_name=f"{config.project_name}_neo4j_data",
            )
            config.docker_compose_path.write_text(content)
            created.append(str(config.docker_compose_path))
        except Exception:
            click.echo("Warning: docker-compose.yml template not found. Skipping.", err=True)

    # 3. .env.example
    if not config.env_example_path.exists():
        try:
            env_tpl = (pkg_files("memoryschema.templates") / "env.example").read_text()
            config.env_example_path.write_text(env_tpl)
            created.append(str(config.env_example_path))
        except Exception:
            click.echo("Warning: env.example template not found. Skipping.", err=True)

    # 4. .claude/rules/
    config.rules_dir.mkdir(parents=True, exist_ok=True)
    scope_list = [s.strip() for s in scopes.split(",")]

    try:
        # Schema rules (always)
        schema_rules = (pkg_files("memoryschema.templates") / "memory-schema.rules.tpl").read_text()
        rules_path = config.rules_dir / "memory-schema.md"
        if not rules_path.exists():
            rules_path.write_text(schema_rules)
            created.append(str(rules_path))

        # Scope guidelines
        for scope in scope_list:
            tpl_name = f"memory-{scope}.tpl"
            try:
                tpl = (pkg_files("memoryschema.templates") / tpl_name).read_text()
                scope_path = config.rules_dir / f"memory-{scope}.md"
                if not scope_path.exists():
                    content = tpl.format(project_name=config.project_name)
                    scope_path.write_text(content)
                    created.append(str(scope_path))
            except Exception:
                click.echo(f"Warning: Template {tpl_name} not found. Skipping.", err=True)
    except Exception:
        click.echo("Warning: Templates not found. Skipping rules setup.", err=True)

    # 5. memoryschema.toml
    toml_path = config.config_file_path
    if not toml_path.exists():
        try:
            tpl = (pkg_files("memoryschema.templates") / "memoryschema.toml.tpl").read_text()
            content = tpl.format(project_name=config.project_name)
            toml_path.write_text(content)
            created.append(str(toml_path))
        except Exception:
            click.echo("Warning: memoryschema.toml template not found. Skipping.", err=True)

    # Report
    if created:
        click.echo("Created:")
        for f in created:
            click.echo(f"  {f}")
    else:
        click.echo("All files already exist.")

    # 5. Optional Neo4j deploy
    if with_neo4j:
        click.echo("\nDeploying Neo4j...")
        ctx = click.get_current_context()
        ctx.invoke(neo4j_deploy_fn, config=config)

    # 6. Hook instructions
    try:
        from importlib.resources import files as _files
        hook_path = str(_files("memoryschema.hooks") / "hook-post-write.sh")
        click.echo(f"\nHook registration — run: memoryschema hook install")
        click.echo(f"  Or add to ~/.claude/settings.json:")
        click.echo(f'  {{"matcher": "Write", "hooks": [{{"type": "command", "command": "bash {hook_path}", "timeout": 10}}]}}')
    except Exception:
        pass

    click.echo(f"\nProject '{config.project_name}' initialized.")


def neo4j_deploy_fn(config):
    """Inline Neo4j deploy for init --with-neo4j."""
    from memoryschema.cli.neo4j_cmd import deploy
    ctx = click.Context(deploy, obj=config)
    ctx.invoke(deploy)


# --- Register subcommand groups ---

from memoryschema.cli.neo4j_cmd import neo4j
from memoryschema.cli.voyage_cmd import voyage
from memoryschema.cli.hook_cmd import hook
from memoryschema.cli.migrate_cmd import migrate, sync

cli.add_command(neo4j)
cli.add_command(voyage)
cli.add_command(hook)
cli.add_command(migrate)
cli.add_command(sync)

# --- Register individual commands ---

from memoryschema.cli.memory_cmd import (
    status, recall, get, list_cmd, write, delete, archive, unarchive,
    reactivate, search, quarantine, force_cmd, decline_cmd,
)
from memoryschema.cli.validate_cmd import validate
from memoryschema.cli.index_cmd import index, embed, associations
from memoryschema.cli.lifecycle_cmd import (
    backup, restore, reset, clean, export_cmd, import_cmd,
)

cli.add_command(status)
cli.add_command(recall)
cli.add_command(get)
cli.add_command(list_cmd, name="list")
cli.add_command(write)
cli.add_command(delete)
cli.add_command(archive)
cli.add_command(unarchive)
cli.add_command(reactivate)
cli.add_command(search)
cli.add_command(quarantine)
cli.add_command(force_cmd, name="force")
cli.add_command(decline_cmd, name="decline")
cli.add_command(validate)
cli.add_command(index)
cli.add_command(embed)
cli.add_command(associations)
cli.add_command(backup)
cli.add_command(restore)
cli.add_command(reset)
cli.add_command(clean)
cli.add_command(export_cmd, name="export")
cli.add_command(import_cmd, name="import")

from memoryschema.cli.doctor_cmd import doctor
from memoryschema.cli.rules_cmd import rules
from memoryschema.cli.config_cmd import config_cmd

from memoryschema.cli.eval_cmd import eval_cmd
from memoryschema.cli.reflect_cmd import reflect as reflect_cmd

cli.add_command(doctor)
cli.add_command(rules)
cli.add_command(config_cmd, name="config")
cli.add_command(eval_cmd, name="eval")
cli.add_command(reflect_cmd, name="reflect")
