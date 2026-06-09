"""CLI command for retrieval evaluation.

Runs the evaluation harness against the fixture store and reports
recall@k, MRR, and nDCG@10 metrics.
"""

import json
import sys

import click


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
@click.pass_obj
def eval_cmd(config, as_json):
    """Run retrieval quality evaluation against fixture store.

    Creates a temporary store with synthetic entities, runs the
    evaluation query set, and reports recall@k, MRR, and nDCG@10.

    Example:
        memoryschema eval
        memoryschema eval --json
    """
    from memoryschema.store import MemoryStore
    import tempfile
    import os

    # Build fixture store in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, 'eval.jsonl')
        store = MemoryStore(store_path)

        from tests.eval.fixtures import build_fixture_entries, build_query_set
        for entry in build_fixture_entries():
            store.upsert(entry)

        from tests.eval.metrics import evaluate_all
        query_set = build_query_set()
        result = evaluate_all(store, query_set)

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo("Retrieval Evaluation Results")
    click.echo("=" * 40)
    click.echo()

    for qr in result['queries']:
        click.echo(f"  {qr['description']}")
        click.echo(f"    recall@5={qr['recall@5']:.2f}  "
                   f"recall@10={qr['recall@10']:.2f}  "
                   f"mrr={qr['mrr']:.2f}  "
                   f"ndcg@10={qr['ndcg@10']:.2f}")
        click.echo()

    avg = result['averages']
    click.echo("Averages:")
    click.echo(f"  recall@5={avg['recall@5']:.3f}  "
               f"recall@10={avg['recall@10']:.3f}  "
               f"mrr={avg['mrr']:.3f}  "
               f"ndcg@10={avg['ndcg@10']:.3f}")
