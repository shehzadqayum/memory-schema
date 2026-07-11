"""Preflight dependency-health command."""
import json
import sys

import click


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output JSON.")
@click.option("--no-auto-start", is_flag=True, help="Do not auto-start a stopped Neo4j container.")
@click.option("--require", "require_csv", default=None,
              help="Comma-separated hard requirements (e.g. neo4j,voyage). Default: from config.")
@click.pass_obj
def preflight(config, as_json, no_auto_start, require_csv):
    """Verify dependencies (Docker, Neo4j, Voyage) are available — the default mode.

    A fast health gate (distinct from the heavy `doctor`): checks the Docker engine, the
    Neo4j container (auto-starting it if merely stopped — never Docker Desktop itself),
    bolt, the schema, and a live Voyage embed. Exits non-zero if a HARD-required
    dependency is down (config.require_neo4j / require_voyage).

    Example:
        memoryschema preflight
        memoryschema preflight --json
        memoryschema preflight --require neo4j,voyage
    """
    from memoryschema.preflight import ensure_backend, format_report

    require = [r.strip() for r in require_csv.split(",") if r.strip()] if require_csv else None
    result = ensure_backend(config, auto_start=not no_auto_start, require=require)
    if as_json:
        click.echo(json.dumps(result))
    else:
        click.echo(format_report(result))
    if not result["ok"]:
        sys.exit(1)
