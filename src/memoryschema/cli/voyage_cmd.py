"""Voyage AI connectivity management."""

import json
import os
import sys
import time

import click


@click.group()
def voyage():
    """Manage Voyage AI connectivity and embeddings.

    Commands: status, test.
    """
    pass


@voyage.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def voyage_status(config, as_json):
    """Check Voyage AI API key, test embedding, show model info.

    Example:
        memoryschema voyage status
    """
    info = {
        "api_key_set": bool(config.voyage_api_key),
        "api_key_prefix": config.voyage_api_key[:8] + "..." if config.voyage_api_key else None,
        "embed_model": config.embed_model,
        "rerank_model": config.rerank_model,
        "dimensions": config.embed_dimensions,
    }

    if config.voyage_api_key:
        try:
            from memoryschema.embeddings import embed_text
            t0 = time.time()
            vec = embed_text("test", config=config)
            latency = time.time() - t0
            info["test_embed"] = "OK"
            info["test_dimensions"] = len(vec)
            info["test_latency_s"] = round(latency, 2)
        except Exception as e:
            info["test_embed"] = f"FAILED: {e}"

    if as_json:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"API key:    {'set (' + info['api_key_prefix'] + ')' if info['api_key_set'] else 'NOT SET'}")
        click.echo(f"Model:      {info['embed_model']}")
        click.echo(f"Rerank:     {info['rerank_model']}")
        click.echo(f"Dimensions: {info['dimensions']}")
        if "test_embed" in info:
            click.echo(f"Test embed: {info['test_embed']}")
            if info.get("test_latency_s"):
                click.echo(f"Latency:    {info['test_latency_s']}s")

        if not info["api_key_set"]:
            click.echo("\nFix: export VOYAGE_API_KEY=voy-xxxxx", err=True)


@voyage.command()
@click.argument("text")
@click.pass_obj
def test(config, text):
    """Embed arbitrary text and print vector stats.

    Example:
        memoryschema voyage test "order block definition"
    """
    if not config.voyage_api_key:
        click.echo("Error: VOYAGE_API_KEY not set.", err=True)
        click.echo("Fix: export VOYAGE_API_KEY=voy-xxxxx", err=True)
        sys.exit(1)

    try:
        from memoryschema.embeddings import embed_text
        t0 = time.time()
        vec = embed_text(text, config=config)
        latency = time.time() - t0

        magnitude = sum(x * x for x in vec) ** 0.5
        click.echo(f"Text:       \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
        click.echo(f"Dimensions: {len(vec)}")
        click.echo(f"Magnitude:  {magnitude:.4f}")
        click.echo(f"First 5:    {[round(v, 4) for v in vec[:5]]}")
        click.echo(f"Latency:    {latency:.2f}s")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
