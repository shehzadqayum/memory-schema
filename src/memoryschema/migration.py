"""
JSONL to Neo4j migration.

Batch migrates entries from the JSONL store to Neo4j.
Requires: pip install memory-schema[neo4j]

Usage:
    from memoryschema.migration import migrate
    migrate(config, batch_size=500, verify_flag=True)
"""

import json
import time

from memoryschema.neo4j_store import connect

from memoryschema.config import ALL_RELATION_TYPES as _RELATION_TYPES
from memoryschema.neo4j_store import _serialize_multispace


def load_jsonl(path):
    """Load all entries from JSONL file."""
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def entry_to_node_props(entry):
    """Convert JSONL entry to Neo4j node properties.

    Must carry the lifecycle/temporal fields (key, valid_from, superseded_at,
    superseded_by, promoted_to) — reconcile rebuilds Neo4j THROUGH this function,
    so a whitelist miss here makes the "rebuildable projection" lossy even when
    the store upsert whitelists are correct (the third whitelist of this class).
    """
    props = {}
    for key in ('name', 'schema', 'type', 'status', 'description', 'importance',
                 'body', 'source', 'filepath', 'prompt', 'reasoning',
                 'project', 'created_at', 'last_accessed', 'access_count',
                 'key', 'valid_from', 'superseded_at', 'superseded_by',
                 'promoted_to'):
        if key in entry and entry[key] is not None:
            props[key] = entry[key]

    obs = entry.get('observations', [])
    props['observations'] = obs
    props['observations_text'] = ' '.join(obs)
    props.setdefault('access_count', 0)

    return props


def migrate_nodes(driver, entries, batch_size=500):
    """Batch-create Memory nodes."""
    total = len(entries)
    created = 0

    for i in range(0, total, batch_size):
        batch = entries[i:i + batch_size]
        node_data = []
        for entry in batch:
            props = entry_to_node_props(entry)
            embedding = entry.get('embedding')
            node_data.append({'props': props, 'embedding': embedding,
                              'multispace': _serialize_multispace(entry)})

        with driver.session() as session:
            # ONE UNWIND folds the MERGE + embedding + multispace into a single round-trip per batch
            # (was 1 + 2N queries — this is the reconcile hot-path). MERGE (not CREATE) on the unique
            # name keeps the import IDEMPOTENT (no ConstraintError on memory_name_unique re-runs).
            # coalesce keeps existing values when a row carries no embedding / multispace.
            # (helios local patch — re-apply on re-vendor.)
            session.run("""
                UNWIND $nodes AS nd
                MERGE (m:Memory {name: nd.props.name})
                SET m += nd.props
                SET m.embedding = coalesce(nd.embedding, m.embedding)
                SET m += coalesce(nd.multispace, {})
            """, nodes=node_data)

        created += len(batch)

    return created


def migrate_relations(driver, entries):
    """Create typed relationship edges."""
    total_rels = 0
    for entry in entries:
        relations = entry.get('relations', [])
        if not relations:
            continue
        name = entry['name']
        for rel in relations:
            target = rel.get('target')
            rel_type = rel.get('type')
            if target and rel_type and rel_type in _RELATION_TYPES and target != name:
                with driver.session() as session:
                    session.run(f"""
                        MATCH (s:Memory {{name: $source}})
                        MERGE (t:Memory {{name: $target}})
                        MERGE (s)-[r:{rel_type}]->(t)
                    """, source=name, target=target)
                    total_rels += 1

    return total_rels


def migrate_associations(driver, entries, batch_size=500):
    """Migrate ASSOCIATED_WITH edges from JSONL associations field."""
    assoc_data = []
    for entry in entries:
        associations = entry.get('associations', [])
        name = entry['name']
        for assoc in associations:
            assoc_name = assoc.get('name')
            score = assoc.get('score', 0)
            if assoc_name:
                assoc_data.append({
                    'source': name,
                    'target': assoc_name,
                    'score': score,
                })

    total = 0
    for i in range(0, len(assoc_data), batch_size):
        batch = assoc_data[i:i + batch_size]
        with driver.session() as session:
            session.run("""
                UNWIND $edges AS e
                MATCH (s:Memory {name: e.source}), (t:Memory {name: e.target})
                MERGE (s)-[a:ASSOCIATED_WITH]->(t)
                SET a.score = e.score
            """, edges=batch)
        total += len(batch)

    return total


def verify(driver, jsonl_entries):
    """Verify migration completeness. Returns dict with comparison stats."""
    with driver.session() as session:
        result = session.run("MATCH (m:Memory) RETURN count(m) AS n")
        neo4j_count = result.single()['n']

        result = session.run("MATCH ()-[a:ASSOCIATED_WITH]->() RETURN count(a) AS n")
        assoc_count = result.single()['n']

        result = session.run("""
            MATCH ()-[r]->()
            WHERE type(r) IN $types
            RETURN count(r) AS n
        """, types=list(_RELATION_TYPES))
        rel_count = result.single()['n']

    return {
        'jsonl_count': len(jsonl_entries),
        'neo4j_count': neo4j_count,
        'match': neo4j_count == len(jsonl_entries),
        'associations': assoc_count,
        'relations': rel_count,
    }


def migrate(config=None, batch_size=500, skip_assoc=False, verify_flag=False, dry_run=False):
    """Migrate JSONL store to Neo4j.

    Args:
        config: MemoryConfig instance. Uses defaults if None.
        batch_size: Nodes per batch.
        skip_assoc: Skip association migration.
        verify_flag: Run verification after migration.
        dry_run: Show stats without migrating.

    Returns:
        Dict with migration stats.
    """
    if config is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()

    store_path = str(config.store_path)
    entries = load_jsonl(store_path)

    stats = {
        'entries': len(entries),
        'embedded': sum(1 for e in entries if e.get('embedding')),
        'with_assoc': sum(1 for e in entries if e.get('associations')),
        'with_rels': sum(1 for e in entries if e.get('relations') and len(e['relations']) > 0),
    }

    if dry_run:
        stats['dry_run'] = True
        return stats

    driver = connect(config=config)        # shared driver build + RETURN 1 probe + friendly auth error

    try:
        t0 = time.time()
        stats['nodes_created'] = migrate_nodes(driver, entries, batch_size)
        stats['relations_created'] = migrate_relations(driver, entries)

        if not skip_assoc:
            stats['associations_created'] = migrate_associations(driver, entries, batch_size)
        else:
            stats['associations_created'] = 0

        stats['duration_s'] = round(time.time() - t0, 1)

        if verify_flag:
            stats['verification'] = verify(driver, entries)

    finally:
        driver.close()

    return stats
