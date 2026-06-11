"""CLI command for retrieval evaluation.

Runs the evaluation harness against the fixture store and reports
recall@k, MRR, and nDCG@10 metrics.
"""

import json
import sys

import click


@click.command()
@click.option("--mode", type=click.Choice(["retrieval", "salience"]),
              default="retrieval", help="Evaluation mode: retrieval quality or write-decision salience.")
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
@click.pass_obj
def eval_cmd(config, mode, as_json):
    """Run evaluation against fixture store.

    Modes:
      retrieval (default) — recall@k, MRR, nDCG@10 against synthetic entities
      salience — precision/recall of write-decision fixtures

    Example:
        memoryschema eval
        memoryschema eval --mode salience
        memoryschema eval --json
    """
    if mode == 'salience':
        _run_salience_eval(as_json)
        return
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


def _run_salience_eval(as_json):
    """Run salience evaluation — write-decision quality against fixtures."""
    from tests.eval.fixtures import build_salience_fixtures
    from tests.eval.metrics import evaluate_salience

    fixtures = build_salience_fixtures()

    # Baseline: all-write decisions (upper bound on recall, lower on precision)
    all_write = [{'excerpt': f['excerpt'], 'decision': 'write'} for f in fixtures]
    # Perfect decisions (for reference)
    perfect = [{'excerpt': f['excerpt'], 'decision': f['decision']} for f in fixtures]

    baseline_result = evaluate_salience(all_write, fixtures)
    perfect_result = evaluate_salience(perfect, fixtures)

    result = {
        'mode': 'salience',
        'fixture_count': len(fixtures),
        'actual_writes': baseline_result['actual_writes'],
        'actual_declines': baseline_result['actual_declines'],
        'baseline_all_write': baseline_result,
        'perfect': perfect_result,
    }

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo("Salience Evaluation — Write-Decision Fixtures")
    click.echo("=" * 50)
    click.echo(f"  Fixtures: {len(fixtures)} ({baseline_result['actual_writes']} write, {baseline_result['actual_declines']} decline)")
    click.echo()
    click.echo("Baseline (all-write):")
    click.echo(f"  precision={baseline_result['precision']:.3f}  recall={baseline_result['recall']:.3f}  f1={baseline_result['f1']:.3f}")
    click.echo()
    click.echo("Perfect:")
    click.echo(f"  precision={perfect_result['precision']:.3f}  recall={perfect_result['recall']:.3f}  f1={perfect_result['f1']:.3f}")
    click.echo()
    click.echo("To evaluate an actual decision source, use the evaluate_salience()")
    click.echo("function from tests.eval.metrics with your decision list.")
