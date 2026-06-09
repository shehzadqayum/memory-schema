"""Lifecycle management — backup, restore, reset, clean, export, import."""

import json
import os
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

import click


@click.command()
@click.option("--output", type=click.Path(), help="Output directory for backup. Default: ./backups/.")
@click.option("--neo4j-only", is_flag=True, help="Backup Neo4j data only.")
@click.option("--jsonl-only", is_flag=True, help="Backup JSONL store only.")
@click.option("--files-only", is_flag=True, help="Backup memory .md files only.")
@click.pass_obj
def backup(config, output, neo4j_only, jsonl_only, files_only):
    """Full or selective backup of the memory system.

    Creates a timestamped archive containing selected components.

    Example:
        memoryschema backup
        memoryschema backup --neo4j-only --output /tmp/neo4j-dump
        memoryschema backup --files-only
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(output) if output else config.project_root / "backups"
    output_dir.mkdir(parents=True, exist_ok=True)

    if jsonl_only:
        dest = output_dir / f"store-{timestamp}.jsonl"
        if config.store_path.exists():
            shutil.copy2(config.store_path, dest)
            click.echo(f"Backed up JSONL store to {dest}")
        else:
            click.echo("Error: JSONL store not found.", err=True)
        return

    if files_only:
        dest = output_dir / f"memory-files-{timestamp}.tar.gz"
        with tarfile.open(dest, "w:gz") as tar:
            memory_dir = config.memory_dir
            if memory_dir.exists():
                for f in sorted(memory_dir.glob("*.md")):
                    tar.add(f, arcname=f.name)
                count = len(list(memory_dir.glob("*.md")))
                click.echo(f"Backed up {count} memory files to {dest}")
            else:
                click.echo("Error: Memory directory not found.", err=True)
        return

    # Full backup
    dest = output_dir / f"backup-{config.project_name}-{timestamp}.tar.gz"
    with tarfile.open(dest, "w:gz") as tar:
        components = []

        # Memory files
        if config.memory_dir.exists():
            for f in sorted(config.memory_dir.rglob("*.md")):
                tar.add(f, arcname=f"memory/{f.relative_to(config.memory_dir)}")
            components.append("memory files")

        # JSONL store
        if config.store_path.exists():
            tar.add(config.store_path, arcname="store.jsonl")
            components.append("JSONL store")

        # Rules
        if config.rules_dir.exists():
            for f in config.rules_dir.glob("*.md"):
                tar.add(f, arcname=f".claude/rules/{f.name}")
            components.append("rules")

        # Docker compose
        if config.docker_compose_path.exists():
            tar.add(config.docker_compose_path, arcname="docker-compose.yml")
            components.append("docker-compose.yml")

    click.echo(f"Backup: {dest}")
    click.echo(f"Contains: {', '.join(components)}")


@click.command()
@click.argument("archive", type=click.Path(exists=True))
@click.option("--confirm", is_flag=True, help="Required. Confirms restore operation.")
@click.pass_obj
def restore(config, archive, confirm):
    """Restore from a backup archive.

    WARNING: Overwrites existing files.

    Example:
        memoryschema restore backups/backup-my-project-20260609.tar.gz --confirm
    """
    if not confirm:
        click.echo("This will OVERWRITE existing memory files and store. Use --confirm to proceed.")
        sys.exit(1)

    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getnames()
        click.echo(f"Restoring {len(members)} files from {archive}...")
        tar.extractall(path=config.project_root)

    click.echo(f"Restored to {config.project_root}")


@click.command()
@click.option("--confirm", is_flag=True, help="Required. Confirms destructive operation.")
@click.option("--neo4j-only", is_flag=True, help="Reset Neo4j only.")
@click.option("--store-only", is_flag=True, help="Reset JSONL store only.")
@click.option("--working-memory-only", is_flag=True, help="Delete working memory files only.")
@click.pass_obj
def reset(config, confirm, neo4j_only, store_only, working_memory_only):
    """Reset memory data (full or selective).

    WARNING: This permanently deletes data.

    Example:
        memoryschema reset --confirm
        memoryschema reset --neo4j-only --confirm
        memoryschema reset --working-memory-only --confirm
    """
    if not confirm:
        click.echo("This will DELETE memory data. Use --confirm to proceed.")
        sys.exit(1)

    if neo4j_only:
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(config.neo4j_uri,
                                           auth=(config.neo4j_user, config.neo4j_password))
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            driver.close()
            click.echo("Neo4j data deleted.")
            from memoryschema.schema import setup_schema
            setup_schema(config)
            click.echo("Schema recreated.")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
        return

    if store_only:
        if config.store_path.exists():
            config.store_path.unlink()
            click.echo(f"Deleted: {config.store_path}")
        else:
            click.echo("JSONL store not found.")
        return

    if working_memory_only:
        memory_dir = config.memory_dir
        deleted = 0
        if memory_dir.exists():
            for f in memory_dir.glob("*.md"):
                if f.name != "MEMORY.md":
                    f.unlink()
                    deleted += 1
        click.echo(f"Deleted {deleted} working memory files.")
        return

    # Full reset
    if config.store_path.exists():
        config.store_path.unlink()
        click.echo(f"Deleted: {config.store_path}")

    memory_dir = config.memory_dir
    if memory_dir.exists():
        deleted = 0
        for f in memory_dir.glob("*.md"):
            if f.name != "MEMORY.md":
                f.unlink()
                deleted += 1
        click.echo(f"Deleted {deleted} memory files.")

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(config.neo4j_uri,
                                       auth=(config.neo4j_user, config.neo4j_password))
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
        click.echo("Neo4j data deleted.")
    except Exception:
        pass  # Neo4j may not be running

    click.echo("Full reset complete.")


@click.command()
@click.option("--confirm", is_flag=True, help="Required. Confirms complete removal.")
@click.option("--dry-run", is_flag=True, help="Show what would be removed.")
@click.pass_obj
def clean(config, confirm, dry_run):
    """Complete removal of memory system from project.

    Removes: memory/ directory, docker-compose.yml, .claude/rules/memory-*,
    stops Neo4j container.

    Example:
        memoryschema clean --dry-run
        memoryschema clean --confirm
    """
    targets = []

    if config.memory_dir.exists():
        targets.append(f"Directory: {config.memory_dir}")
    if config.docker_compose_path.exists():
        targets.append(f"File: {config.docker_compose_path}")
    if config.rules_dir.exists():
        for f in config.rules_dir.glob("memory-*"):
            targets.append(f"Rule: {f}")
    if config.env_example_path.exists():
        targets.append(f"File: {config.env_example_path}")

    if not targets:
        click.echo("Nothing to clean.")
        return

    click.echo("Will remove:")
    for t in targets:
        click.echo(f"  {t}")

    if dry_run:
        click.echo("\n(dry run — no changes made)")
        return

    if not confirm:
        click.echo("\nUse --confirm to proceed.")
        sys.exit(1)

    # Stop Neo4j
    if config.docker_compose_path.exists():
        import subprocess
        try:
            subprocess.run(["docker", "compose", "-f", str(config.docker_compose_path), "down"],
                          capture_output=True)
            click.echo("Stopped Neo4j container.")
        except Exception:
            pass

    # Remove files
    if config.memory_dir.exists():
        shutil.rmtree(config.memory_dir)
        click.echo(f"Removed: {config.memory_dir}")
    if config.docker_compose_path.exists():
        config.docker_compose_path.unlink()
        click.echo(f"Removed: {config.docker_compose_path}")
    if config.rules_dir.exists():
        for f in config.rules_dir.glob("memory-*"):
            f.unlink()
            click.echo(f"Removed: {f}")
    if config.env_example_path.exists():
        config.env_example_path.unlink()
        click.echo(f"Removed: {config.env_example_path}")

    click.echo("Clean complete.")


@click.command("export")
@click.option("--format", "fmt", type=click.Choice(["tar", "jsonl", "md"]), default="tar",
              help="Export format. Default: tar.")
@click.option("--output", type=click.Path(), help="Output path.")
@click.pass_obj
def export_cmd(config, fmt, output):
    """Export memory system as a portable archive.

    Formats:
      tar   — memory files + JSONL + rules + docker-compose.yml
      jsonl — all entities as JSONL
      md    — all entities as .md files in a directory

    Example:
        memoryschema export --format tar --output my-export.tar.gz
        memoryschema export --format jsonl --output entities.jsonl
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if fmt == "tar":
        dest = output or f"export-{config.project_name}-{timestamp}.tar.gz"
        with tarfile.open(dest, "w:gz") as tar:
            if config.memory_dir.exists():
                for f in config.memory_dir.rglob("*.md"):
                    tar.add(f, arcname=f"memory/{f.relative_to(config.memory_dir)}")
            if config.store_path.exists():
                tar.add(config.store_path, arcname="store.jsonl")
            if config.rules_dir.exists():
                for f in config.rules_dir.glob("memory-*"):
                    tar.add(f, arcname=f"rules/{f.name}")
            if config.docker_compose_path.exists():
                tar.add(config.docker_compose_path, arcname="docker-compose.yml")
        click.echo(f"Exported to {dest}")

    elif fmt == "jsonl":
        from memoryschema.store import get_store
        store = get_store(config=config)
        entries = store.list_all()
        dest = output or f"export-{config.project_name}-{timestamp}.jsonl"
        with open(dest, 'w', encoding='utf-8') as f:
            for entry in entries:
                e = {k: v for k, v in entry.items() if k != 'embedding'}
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
        click.echo(f"Exported {len(entries):,} entities to {dest}")

    elif fmt == "md":
        dest = Path(output) if output else Path(f"export-{config.project_name}-{timestamp}")
        dest.mkdir(parents=True, exist_ok=True)
        count = 0
        if config.memory_dir.exists():
            for f in config.memory_dir.glob("*.md"):
                shutil.copy2(f, dest / f.name)
                count += 1
        click.echo(f"Exported {count} files to {dest}")


@click.command("import")
@click.argument("source", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["tar", "jsonl", "md"]),
              help="Import format. Auto-detected if omitted.")
@click.pass_obj
def import_cmd(config, source, fmt):
    """Import from a portable archive or file.

    Example:
        memoryschema import export-my-project.tar.gz
        memoryschema import entities.jsonl --format jsonl
    """
    source_path = Path(source)

    if fmt is None:
        if source_path.suffix in ('.gz', '.tar'):
            fmt = "tar"
        elif source_path.suffix == '.jsonl':
            fmt = "jsonl"
        elif source_path.is_dir():
            fmt = "md"
        else:
            click.echo("Error: Cannot detect format. Use --format.", err=True)
            sys.exit(1)

    if fmt == "tar":
        with tarfile.open(source, "r:gz") as tar:
            tar.extractall(path=config.project_root)
        click.echo(f"Imported archive to {config.project_root}")

    elif fmt == "jsonl":
        from memoryschema.store import get_store
        store = get_store(config=config)
        count = 0
        with open(source, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    store.upsert(entry)
                    count += 1
        click.echo(f"Imported {count:,} entities.")

    elif fmt == "md":
        from memoryschema.tags import parse_memory_file
        from memoryschema.store import get_store
        store = get_store(config=config)
        count = 0
        for f in sorted(source_path.glob("*.md")):
            memory = parse_memory_file(str(f))
            if memory:
                store.upsert(memory)
                count += 1
        click.echo(f"Imported {count} entities from .md files.")
