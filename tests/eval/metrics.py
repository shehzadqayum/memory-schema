"""Retrieval quality metrics for evaluation.

Computes recall@k, MRR, and nDCG@k from retrieval results
against gold relevant-entity labels.
"""

import math


def recall_at_k(retrieved_names, relevant_names, k=5):
    """Fraction of relevant items found in top-k results.

    Returns float in [0.0, 1.0].
    """
    if not relevant_names:
        return 1.0  # No relevant items = perfect recall (abstention)
    top_k = set(retrieved_names[:k])
    relevant = set(relevant_names)
    return len(top_k & relevant) / len(relevant)


def mrr(retrieved_names, relevant_names):
    """Mean Reciprocal Rank — 1/rank of first relevant result.

    Returns float in [0.0, 1.0]. 0 if no relevant found.
    """
    if not relevant_names:
        return 1.0
    relevant = set(relevant_names)
    for i, name in enumerate(retrieved_names):
        if name in relevant:
            return 1.0 / (i + 1)
    return 0.0


def dcg_at_k(retrieved_names, relevant_names, k=10):
    """Discounted Cumulative Gain at k.

    Binary relevance: 1 if in relevant set, 0 otherwise.
    """
    relevant = set(relevant_names)
    dcg = 0.0
    for i, name in enumerate(retrieved_names[:k]):
        if name in relevant:
            dcg += 1.0 / math.log2(i + 2)  # +2 because log2(1)=0
    return dcg


def ndcg_at_k(retrieved_names, relevant_names, k=10):
    """Normalized DCG at k.

    Returns float in [0.0, 1.0].
    """
    if not relevant_names:
        return 1.0
    actual_dcg = dcg_at_k(retrieved_names, relevant_names, k)
    # Ideal DCG: all relevant items ranked first
    ideal_names = list(relevant_names)[:k]
    ideal_dcg = dcg_at_k(ideal_names, relevant_names, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def evaluate_query(store, query_spec):
    """Run a single query against the store and compute metrics.

    Args:
        store: MemoryStore instance.
        query_spec: Dict with 'query', 'relevant', 'project', 'description'.

    Returns:
        Dict with metrics: recall@5, recall@10, mrr, ndcg@10, retrieved.
    """
    results = store.recall(
        query=query_spec['query'],
        project=query_spec.get('project'),
        limit=20,
    )
    retrieved = [r['name'] for r in results]
    relevant = query_spec['relevant']

    return {
        'query': query_spec['query'],
        'description': query_spec['description'],
        'recall@5': recall_at_k(retrieved, relevant, k=5),
        'recall@10': recall_at_k(retrieved, relevant, k=10),
        'mrr': mrr(retrieved, relevant),
        'ndcg@10': ndcg_at_k(retrieved, relevant, k=10),
        'retrieved_count': len(retrieved),
        'relevant_count': len(relevant),
    }


def evaluate_all(store, query_set):
    """Run all queries and compute aggregate metrics.

    Returns:
        Dict with per-query results and aggregate averages.
    """
    per_query = [evaluate_query(store, q) for q in query_set]

    n = len(per_query)
    if n == 0:
        return {'queries': [], 'averages': {}}

    averages = {
        'recall@5': sum(r['recall@5'] for r in per_query) / n,
        'recall@10': sum(r['recall@10'] for r in per_query) / n,
        'mrr': sum(r['mrr'] for r in per_query) / n,
        'ndcg@10': sum(r['ndcg@10'] for r in per_query) / n,
    }

    return {
        'queries': per_query,
        'averages': averages,
    }


def evaluate_salience(decisions, fixtures):
    """Evaluate write-decision quality against gold-labelled fixtures.

    Args:
        decisions: list of {"excerpt": str, "decision": "write"|"decline"}
            from the system under test.
        fixtures: list of {"excerpt": str, "decision": str, "reason": str}
            gold labels from build_salience_fixtures().

    Returns:
        Dict with precision, recall, f1, total, correct, and baseline scores.
    """
    # Build lookup from excerpt → gold decision
    gold = {f['excerpt']: f['decision'] for f in fixtures}

    # Count
    total = 0
    correct = 0
    true_positives = 0   # predicted write AND gold write
    false_positives = 0  # predicted write AND gold decline
    false_negatives = 0  # predicted decline AND gold write

    for d in decisions:
        excerpt = d['excerpt']
        predicted = d['decision']
        actual = gold.get(excerpt)
        if actual is None:
            continue  # skip unmatched excerpts
        total += 1
        if predicted == actual:
            correct += 1
        if predicted == 'write' and actual == 'write':
            true_positives += 1
        elif predicted == 'write' and actual == 'decline':
            false_positives += 1
        elif predicted == 'decline' and actual == 'write':
            false_negatives += 1

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Baselines
    actual_writes = sum(1 for f in fixtures if f['decision'] == 'write')
    actual_declines = len(fixtures) - actual_writes
    all_write_precision = actual_writes / len(fixtures) if fixtures else 0.0
    all_decline_recall = 0.0  # declining everything catches zero writes

    return {
        'total': total,
        'correct': correct,
        'accuracy': correct / total if total > 0 else 0.0,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'baseline_all_write_precision': round(all_write_precision, 4),
        'fixture_count': len(fixtures),
        'actual_writes': actual_writes,
        'actual_declines': actual_declines,
    }
