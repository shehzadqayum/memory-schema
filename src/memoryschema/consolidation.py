"""
Batch memory consolidation and reflection.

Two operations:
- consolidate(): batch index un-indexed memory files
- reflect(): cluster episodic entries and synthesise summaries

Reflection implements the episodic→semantic pattern from the
agent-memory literature: group related episodes, create a semantic
summary with SUPERSEDES edges, archive the originals.
"""

import sys
from datetime import datetime, timezone

from memoryschema.tags import parse_memory_file
from memoryschema.discovery import discover_memory_files
from memoryschema.store import MemoryStore


def _embedding_text(memory):
    """Compose the text to embed for a memory.

    Uses name + description + observations + prompt + reasoning.
    """
    parts = [memory.get('name', ''), memory.get('description', '')]
    parts.extend(memory.get('observations', []))
    if memory.get('prompt'):
        parts.append(memory['prompt'])
    if memory.get('reasoning'):
        parts.append(memory['reasoning'])
    return ' '.join(parts)


def consolidate(base_path, project, store, embed=False):
    """Discover and index all memory files under base_path.

    Parses each file via tags.py, upserts into the store,
    recomputes backlinks, and optionally embeds via Voyage.

    Args:
        base_path: Root directory containing memory .md files.
        project: Project name for scoping.
        store: MemoryStore or Neo4jMemoryStore instance.
        embed: If True, embed each memory via Voyage and compute associations.

    Returns:
        Dict with counts: {synced, skipped, backlinks, embedded, associations}.
    """
    filepaths = discover_memory_files(base_path)
    synced = 0
    skipped = 0
    embedded = 0

    embed_fn = None
    if embed:
        try:
            from memoryschema.embeddings import embed_text
            embed_fn = embed_text
        except (ImportError, Exception):
            print('Warning: embeddings unavailable, skipping embedding', file=sys.stderr)

    for filepath in filepaths:
        memory = parse_memory_file(filepath)
        if memory is None:
            skipped += 1
            continue
        if memory.get('project') is None:
            memory['project'] = project

        if embed_fn:
            existing = store.get(memory.get('name'))
            if not existing or not existing.get('embedding'):
                try:
                    text = _embedding_text(memory)
                    memory['embedding'] = embed_fn(text)
                    embedded += 1
                except Exception:
                    pass

        store.upsert(memory)
        synced += 1

    backlinks = store.compute_backlinks() if synced > 0 else 0
    associations = 0
    if embedded > 0:
        associations = store.compute_associations()

    return {
        'synced': synced,
        'skipped': skipped,
        'backlinks': backlinks,
        'embedded': embedded,
        'associations': associations,
    }


def _cluster_by_associations(entries, min_cluster=2, max_cluster=10):
    """Group entries by association neighbourhood (connected components).

    Returns list of clusters (each a list of entry dicts).
    Only returns clusters with min_cluster <= size <= max_cluster.
    """
    # Build adjacency from associations
    name_to_entry = {e['name']: e for e in entries}
    adjacency = {e['name']: set() for e in entries}
    for entry in entries:
        for assoc in entry.get('associations', []):
            target = assoc.get('name') or assoc.get('target')
            if target and target in adjacency:
                adjacency[entry['name']].add(target)
                adjacency[target].add(entry['name'])

    # Connected components via BFS
    visited = set()
    clusters = []
    for name in adjacency:
        if name in visited:
            continue
        component = []
        queue = [name]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current in name_to_entry:
                component.append(name_to_entry[current])
            for neighbour in adjacency.get(current, []):
                if neighbour not in visited:
                    queue.append(neighbour)
        if min_cluster <= len(component) <= max_cluster:
            clusters.append(component)
    return clusters


def _synthesise_summary(cluster):
    """Create a summary entity from a cluster of episodic entries.

    Uses Anthropic SDK if available for LLM synthesis.
    Falls back to mechanical merge (concatenate observations).
    """
    names = [e['name'] for e in cluster]
    all_obs = []
    all_desc = []
    project = None
    for entry in cluster:
        if entry.get('description'):
            all_desc.append(entry['description'])
        all_obs.extend(entry.get('observations', []))
        if not project and entry.get('project'):
            project = entry['project']

    # Try LLM synthesis
    try:
        import anthropic
        client = anthropic.Anthropic()
        prompt = (
            f"Synthesise these {len(cluster)} episodic memory entries into "
            f"one concise semantic summary. Return only the summary text "
            f"(1-2 sentences).\n\n"
            + "\n".join(f"- {d}" for d in all_desc)
        )
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        description = response.content[0].text.strip()
    except Exception:
        # Mechanical fallback: join descriptions
        description = '; '.join(all_desc[:5])
        if len(all_desc) > 5:
            description += f' (+{len(all_desc) - 5} more)'

    # Deduplicate observations
    seen = set()
    unique_obs = []
    for obs in all_obs:
        if obs not in seen:
            unique_obs.append(obs)
            seen.add(obs)

    summary_name = f"summary-{names[0]}"
    now = datetime.now(timezone.utc).isoformat()

    return {
        'name': summary_name,
        'schema': 4,
        'type': 'semantic',
        'status': 'active',
        'importance': max(e.get('importance') or 5 for e in cluster),
        'description': description,
        'observations': unique_obs[:10],
        'relations': [{'target': n, 'type': 'SUPERSEDES'} for n in names],
        'project': project,
        'source': 'reflection',
        'created_at': now,
        'last_accessed': now,
        'access_count': 0,
    }


def _check_cluster_contradictions(cluster):
    """Check a cluster for contradictions before synthesis.

    Returns a list of reason strings if contradictions found, empty list otherwise.
    Checks: (a) CONTRADICTS relations between members, (b) numeric contradictions.
    """
    reasons = []
    member_names = {e['name'] for e in cluster}

    # (a) CONTRADICTS relations between members
    for entry in cluster:
        for rel in entry.get('relations', []):
            if rel.get('type') == 'CONTRADICTS' and rel.get('target') in member_names:
                reasons.append(
                    f"CONTRADICTS between {entry['name']} and {rel['target']}")
        for bl in entry.get('backlinks', []):
            if bl.get('type') == 'CONTRADICTS' and bl.get('source') in member_names:
                reasons.append(
                    f"CONTRADICTS between {bl['source']} and {entry['name']}")

    # (b) Numeric contradictions via numeric_probe
    try:
        from memoryschema.numeric_probe import extract_entity_claims, compare
        for i, entry in enumerate(cluster):
            candidate_claims = extract_entity_claims(entry)
            if candidate_claims:
                others = cluster[:i] + cluster[i+1:]
                hits = compare(candidate_claims, others)
                for hit in hits:
                    qual = f"/{hit['qualifier']}" if hit['qualifier'] else ''
                    reasons.append(
                        f"numeric-contradiction: {hit['unit']}{qual} "
                        f"{hit['candidate_value']} vs {hit['neighbour_value']} "
                        f"({entry['name']} vs {hit['neighbour_name']})")
    except ImportError:
        pass

    # Deduplicate (symmetric CONTRADICTS can produce duplicates)
    return list(dict.fromkeys(reasons))


def reflect(store, project=None, min_cluster=2, max_cluster=10,
            dry_run=False, include_contradictory=False):
    """Cluster episodic entries and synthesise semantic summaries.

    For each cluster of related episodic entries (grouped by
    association neighbourhood):
    1. Check for contradictions (CONTRADICTS relations + numeric probe)
    2. Skip contradictory clusters (or synthesize with --include-contradictory)
    3. Synthesise a semantic summary entity
    4. Create SUPERSEDES edges from summary to members
    5. Archive the original episodic entries

    Args:
        store: MemoryStore or Neo4jMemoryStore instance.
        project: Optional project scope.
        min_cluster: Minimum cluster size to process.
        max_cluster: Maximum cluster size to process.
        dry_run: If True, return clusters without creating summaries.
        include_contradictory: If True, synthesize contradictory clusters
            with min importance, CONTRADICTS edges, and inferred basis.

    Returns:
        Dict with counts: {clusters, summaries, archived, skipped, dry_run}.
    """
    entries = store.list_all(project=project, include_inactive=True)
    episodic = [e for e in entries
                if e.get('type') == 'episodic'
                and e.get('status', 'active') == 'active']

    clusters = _cluster_by_associations(episodic, min_cluster, max_cluster)

    stats = {
        'clusters': len(clusters),
        'summaries': 0,
        'archived': 0,
        'skipped': 0,
        'dry_run': dry_run,
    }

    if dry_run or not clusters:
        return stats

    for cluster in clusters:
        # Pre-synthesis contradiction check
        contradiction_reasons = _check_cluster_contradictions(cluster)

        if contradiction_reasons and not include_contradictory:
            # Skip: no synthesis, no SUPERSEDES, members untouched
            stats['skipped'] += 1
            try:
                store._audit('reflect_skip', cluster[0]['name'], {
                    'members': [e['name'] for e in cluster],
                    'reasons': contradiction_reasons,
                })
            except Exception:
                pass
            continue

        if contradiction_reasons and include_contradictory:
            # Synthesize with degraded authority
            summary = _synthesise_contradictory_summary(cluster, contradiction_reasons)
        else:
            summary = _synthesise_summary(cluster)

        store.upsert(summary)
        stats['summaries'] += 1

        for entry in cluster:
            store.archive(entry['name'])
            stats['archived'] += 1

    return stats


def _synthesise_contradictory_summary(cluster, contradiction_reasons):
    """Synthesize a summary for a contradictory cluster with degraded authority.

    - importance = min of cluster (not max)
    - CONTRADICTS relations to each conflicting member
    - all observations labelled basis="inferred"
    """
    from memoryschema.tags import Observation

    summary = _synthesise_summary(cluster)

    # Force min importance
    summary['importance'] = min(e.get('importance') or 5 for e in cluster)

    # Add CONTRADICTS relations to conflicting members
    conflicting_names = set()
    for reason in contradiction_reasons:
        for entry in cluster:
            if entry['name'] in reason:
                conflicting_names.add(entry['name'])
    for cname in conflicting_names:
        if not any(r.get('target') == cname and r.get('type') == 'CONTRADICTS'
                   for r in summary['relations']):
            summary['relations'].append({'target': cname, 'type': 'CONTRADICTS'})

    # Label all observations as inferred
    summary['observations'] = [
        Observation(str(o), basis='inferred') for o in summary['observations']
    ]

    return summary
