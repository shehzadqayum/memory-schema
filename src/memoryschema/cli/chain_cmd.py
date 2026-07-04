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


@chain.command("step")
@click.argument("text", required=False)
@click.option("--stdin", "use_stdin", is_flag=True,
              help="Read the step text from stdin (long text without shell quoting).")
@click.option("--desc", default=None,
              help="Replace the chain's evolving description/summary.")
@click.option("--reasoning", default=None,
              help="Append narrative reasoning (after a '---' separator).")
@click.option("--uses", multiple=True,
              help="Add a USES relation to an evidence memory (repeatable).")
@click.option("--no-index", is_flag=True, help="Write the file only; skip indexing.")
@click.pass_obj
def chain_step(config, text, use_stdin, desc, reasoning, uses, no_index):
    """Append one step to the ACTIVE chain — plain text in, valid entity out.

    The deterministic chain-update path: code does the step numbering, the
    XML escaping (raw '<'/'&' in prose are safe here), the anchored append,
    parse-validation with rollback, and the full index pipeline (embed,
    gate, Neo4j+JSONL dual-write, L0 rebuild). Replaces the hand-edited
    3-Edit protocol.

    Example:
        memoryschema chain step "Fixed the clamp bug (p._total < vis is fine here)" \\
            --desc "Chain summary so far..." --uses some-evidence-memory
    """
    import os
    import sys
    from memoryschema.chain_state import get_active_chain
    from memoryschema.write_index import append_chain_step, index_memory

    project_root = str(config.project_root) if config and config.project_root else '.'
    active = get_active_chain(project_root)
    if not active:
        click.echo("Error: no active chain. Start one: memoryschema chain start <name>", err=True)
        raise SystemExit(1)

    if use_stdin:
        text = sys.stdin.read()
    if not text or not text.strip():
        click.echo("Error: no step text (pass TEXT or --stdin).", err=True)
        raise SystemExit(1)

    chain_path = os.path.join(project_root, "memory", f"{active}.md")
    if not os.path.exists(chain_path):
        # Bootstrap: chain start only authorises the NAME; the first step creates
        # the file (v5 skeleton). Mirrors the old first-Write-creates-it protocol.
        from memoryschema.format_v5 import serialize_v5
        skeleton = serialize_v5({"schema": 5, "name": active,
                                 "description": desc or f"Working chain {active}.",
                                 "log": [], "observations": []})
        with open(chain_path, "w", encoding="utf-8", newline="") as f:
            f.write(skeleton)
        click.echo(f"{active}: chain file created")

    try:
        step_no = append_chain_step(chain_path, text, desc=desc,
                                    reasoning=reasoning, uses=list(uses))
    except (ValueError, OSError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"{active}: step {step_no} written"
               + (" · desc updated" if desc else "")
               + (" · reasoning appended" if reasoning else "")
               + (f" · +{len(uses)} USES" if uses else ""))

    if not no_index:
        res = index_memory(chain_path, config=config)
        _probe = [w for w in res.warnings if '[numeric-probe-hit]' in str(w)]
        _other = [w for w in res.warnings if '[numeric-probe-hit]' not in str(w)]
        for w in _other[:5]:
            click.echo(f"  warn: {w}", err=True)
        if len(_other) > 5:
            click.echo(f"  warn: (+{len(_other)-5} more)", err=True)
        if _probe:  # the v4 numeric probe is noisy on number-dense chain prose — summarize
            click.echo(f"  warn: numeric-probe: {len(_probe)} cross-entity number mismatches (advisory)", err=True)
        click.echo(f"  {res.summary()}")
        if not res.ok:
            raise SystemExit(1)
