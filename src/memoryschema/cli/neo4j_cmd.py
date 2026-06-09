"""Neo4j Docker container management."""

import json
import subprocess
import sys
import time

import click


@click.group()
def neo4j():
    """Manage Neo4j Docker container lifecycle.

    Commands: deploy, up, down, status, logs, schema, reset, shell.
    """
    pass


@neo4j.command()
@click.pass_obj
def deploy(config):
    """Full first-time setup: pull image, start container, create schema, verify.

    Runs the complete Neo4j deployment pipeline in one command.
    Requires Docker to be installed and running.

    Example:
        memoryschema neo4j deploy
    """
    # Check Docker
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        click.echo("Error: Docker is not installed or not running.", err=True)
        click.echo("Fix: Install Docker from https://docker.com and start the daemon.", err=True)
        sys.exit(1)

    compose_path = config.docker_compose_path
    if not compose_path.exists():
        click.echo(f"Error: {compose_path} not found.", err=True)
        click.echo("Fix: Run 'memoryschema init' first to generate docker-compose.yml.", err=True)
        sys.exit(1)

    click.echo(f"Pulling Neo4j image...")
    subprocess.run(["docker", "compose", "-f", str(compose_path), "pull"], check=True)

    click.echo(f"Starting {config.neo4j_container_name}...")
    subprocess.run(["docker", "compose", "-f", str(compose_path), "up", "-d"], check=True)

    # Wait for healthcheck
    click.echo("Waiting for Neo4j to be ready...")
    for i in range(30):
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", config.neo4j_container_name],
                capture_output=True, text=True)
            if "healthy" in result.stdout:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        click.echo("Warning: Healthcheck timeout after 60s. Neo4j may still be starting.", err=True)

    # Create schema
    click.echo("Creating Neo4j schema...")
    try:
        from memoryschema.schema import setup_schema
        indexes = setup_schema(config)
        click.echo(f"Created {len(indexes)} indexes.")
    except Exception as e:
        click.echo(f"Warning: Schema creation failed: {e}", err=True)
        click.echo("Fix: Run 'memoryschema neo4j schema' once Neo4j is fully started.", err=True)

    # Verify
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore(config=config)
        count = store.count()
        click.echo(f"\nDeployment complete.")
        click.echo(f"  Container: {config.neo4j_container_name}")
        click.echo(f"  Bolt: {config.neo4j_uri}")
        click.echo(f"  HTTP: http://localhost:{config.neo4j_http_port}")
        click.echo(f"  Nodes: {count}")
        store.close()
    except Exception as e:
        click.echo(f"Warning: Verification failed: {e}", err=True)


@neo4j.command()
@click.pass_obj
def up(config):
    """Start existing Neo4j container.

    Example:
        memoryschema neo4j up
    """
    compose_path = config.docker_compose_path
    if not compose_path.exists():
        click.echo(f"Error: {compose_path} not found.", err=True)
        click.echo("Fix: Run 'memoryschema init' first.", err=True)
        sys.exit(1)

    subprocess.run(["docker", "compose", "-f", str(compose_path), "up", "-d"], check=True)
    click.echo(f"Started {config.neo4j_container_name}.")


@neo4j.command()
@click.pass_obj
def down(config):
    """Stop Neo4j container.

    Example:
        memoryschema neo4j down
    """
    compose_path = config.docker_compose_path
    if not compose_path.exists():
        click.echo(f"Error: {compose_path} not found.", err=True)
        sys.exit(1)

    subprocess.run(["docker", "compose", "-f", str(compose_path), "down"], check=True)
    click.echo(f"Stopped {config.neo4j_container_name}.")


@neo4j.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def neo4j_status(config, as_json):
    """Show Neo4j container status, connectivity, and store stats.

    Example:
        memoryschema neo4j status
        memoryschema neo4j status --json
    """
    info = {"container": config.neo4j_container_name, "uri": config.neo4j_uri}

    # Docker availability
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        docker_available = True
    except (FileNotFoundError, subprocess.CalledProcessError):
        docker_available = False

    info["docker_available"] = docker_available

    # Container status
    if docker_available:
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={config.neo4j_container_name}",
                 "--format", "{{.Status}}"],
                capture_output=True, text=True)
            container_status = result.stdout.strip() or "not created"
        except Exception:
            container_status = "unknown"
    else:
        container_status = "n/a"

    info["container_status"] = container_status

    # Connectivity
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        store = Neo4jMemoryStore(config=config)
        info["connected"] = True
        info["nodes"] = store.count()
        store.close()
    except Exception:
        info["connected"] = False
        info["nodes"] = None

    if as_json:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"Container: {info['container']}")
        click.echo(f"Docker:    {'installed' if info['docker_available'] else 'not found'}")
        click.echo(f"Status:    {info['container_status']}")
        click.echo(f"URI:       {info['uri']}")
        click.echo(f"Connected: {'yes' if info['connected'] else 'no'}")
        if info['nodes'] is not None:
            click.echo(f"Nodes:     {info['nodes']:,}")


@neo4j.command()
@click.option("--tail", default=50, help="Number of log lines to show. Default: 50.")
@click.pass_obj
def logs(config, tail):
    """Stream Neo4j container logs.

    Example:
        memoryschema neo4j logs
        memoryschema neo4j logs --tail 100
    """
    compose_path = config.docker_compose_path
    subprocess.run(["docker", "compose", "-f", str(compose_path), "logs",
                    "--tail", str(tail), "-f"])


@neo4j.command("schema")
@click.pass_obj
def neo4j_schema(config):
    """Create or verify Neo4j indexes and constraints (idempotent).

    Creates: unique constraint, vector index, full-text index, range indexes.

    Example:
        memoryschema neo4j schema
    """
    try:
        from memoryschema.schema import setup_schema
        indexes = setup_schema(config)
        click.echo(f"Schema verified: {len(indexes)} indexes.")
        for idx in indexes:
            click.echo(f"  {idx.get('name', '?')} — {idx.get('type', '?')}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Fix: Ensure Neo4j is running. Run: memoryschema neo4j up", err=True)
        sys.exit(1)


@neo4j.command()
@click.option("--confirm", is_flag=True, help="Required. Confirms destructive operation.")
@click.pass_obj
def reset(config, confirm):
    """Reset Neo4j: drop all data, recreate schema.

    WARNING: This deletes all Memory nodes and edges.

    Example:
        memoryschema neo4j reset --confirm
    """
    if not confirm:
        click.echo("This will DELETE all Neo4j data. Use --confirm to proceed.")
        sys.exit(1)

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(config.neo4j_uri,
                                       auth=(config.neo4j_user, config.neo4j_password))
        with driver.session() as session:
            result = session.run("MATCH (m:Memory) RETURN count(m) AS n")
            count = result.single()['n']
            click.echo(f"Deleting {count:,} nodes...")
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
        click.echo("All data deleted.")

        from memoryschema.schema import setup_schema
        setup_schema(config)
        click.echo("Schema recreated.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@neo4j.command()
@click.pass_obj
def shell(config):
    """Open Cypher shell in the Neo4j container.

    Example:
        memoryschema neo4j shell
    """
    subprocess.run([
        "docker", "exec", "-it", config.neo4j_container_name,
        "cypher-shell", "-u", config.neo4j_user, "-p", config.neo4j_password,
    ])
