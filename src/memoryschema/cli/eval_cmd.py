"""CLI command for retrieval and salience evaluation.

Modes:
  retrieval — recall@k, MRR, nDCG@10 against real or fixture store
  salience  — precision/recall of write-decision fixtures + audit log scoring
"""

import json
import sys

import click


@click.command()
@click.option("--mode", type=click.Choice(["retrieval", "salience"]),
              default="retrieval", help="Evaluation mode: retrieval quality or write-decision salience.")
@click.option("--store", "store_path", default=None, type=click.Path(),
              help="Path to store.jsonl for real-data eval. Default: configured store.")
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
@click.pass_obj
def eval_cmd(config, mode, store_path, as_json):
    """Run evaluation against real or fixture store.

    Modes:
      retrieval (default) — recall@k, MRR, nDCG@10
        Without --store: runs against synthetic fixture store
        With --store: runs against real data (the single-space baseline)

      salience — precision/recall of write-decision fixtures

    Example:
        memoryschema eval
        memoryschema eval --store memory/store.jsonl
        memoryschema eval --mode salience
        memoryschema eval --json
    """
    if mode == 'salience':
        _run_salience_eval(as_json)
        return

    _run_retrieval_eval(config, store_path, as_json)


def _run_retrieval_eval(config, store_path, as_json):
    """Run retrieval evaluation — synthetic fixtures or real store."""
    from memoryschema.store import MemoryStore
    from memoryschema.eval.fixtures import build_fixture_entries, build_query_set
    from memoryschema.eval.metrics import evaluate_all

    if store_path:
        # Real-data evaluation against actual store
        from memoryschema.eval.fixtures import build_real_data_query_set
        store = MemoryStore(store_path)
        query_set = build_real_data_query_set()
        source = f"real store ({store_path})"
    else:
        # Synthetic fixture evaluation
        import tempfile
        import os
        tmpdir = tempfile.mkdtemp()
        fixture_path = os.path.join(tmpdir, 'eval.jsonl')
        store = MemoryStore(fixture_path)
        for entry in build_fixture_entries():
            store.upsert(entry)
        query_set = build_query_set()
        source = "synthetic fixtures"

    result = evaluate_all(store, query_set)
    result['source'] = source

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"Retrieval Evaluation ({source})")
    click.echo("=" * 50)
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
    from memoryschema.eval.fixtures import build_salience_fixtures
    from memoryschema.eval.metrics import evaluate_salience
    from memoryschema.eval.salience_scorer import classify_salience

    fixtures = build_salience_fixtures()

    # Baseline: all-write decisions (upper bound on recall, lower on precision)
    all_write = [{'excerpt': f['excerpt'], 'decision': 'write'} for f in fixtures]
    # Perfect decisions (for reference)
    perfect = [{'excerpt': f['excerpt'], 'decision': f['decision']} for f in fixtures]
    # System: the measured heuristic classifier (a coded proxy, not the LLM)
    system = [{'excerpt': f['excerpt'], 'decision': classify_salience(f['excerpt'])}
              for f in fixtures]

    baseline_result = evaluate_salience(all_write, fixtures)
    perfect_result = evaluate_salience(perfect, fixtures)
    system_result = evaluate_salience(system, fixtures)

    result = {
        'mode': 'salience',
        'fixture_count': len(fixtures),
        'actual_writes': baseline_result['actual_writes'],
        'actual_declines': baseline_result['actual_declines'],
        'system_heuristic': system_result,
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
    click.echo("System (heuristic — coded proxy, not the LLM):")
    click.echo(f"  precision={system_result['precision']:.3f}  recall={system_result['recall']:.3f}  f1={system_result['f1']:.3f}  accuracy={system_result['accuracy']:.3f}")
    click.echo()
    click.echo("Baseline (all-write):")
    click.echo(f"  precision={baseline_result['precision']:.3f}  recall={baseline_result['recall']:.3f}  f1={baseline_result['f1']:.3f}")
    click.echo()
    click.echo("Perfect:")
    click.echo(f"  precision={perfect_result['precision']:.3f}  recall={perfect_result['recall']:.3f}  f1={perfect_result['f1']:.3f}")
