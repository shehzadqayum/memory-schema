"""
Neo4j-backed memory store (L2b).

Drop-in replacement for MemoryStore backed by Neo4j.
Provides O(1) upserts, native vector k-NN, and graph traversal.

Requires: pip install memory-schema[neo4j]

Usage:
    from memoryschema import Neo4jMemoryStore
    store = Neo4jMemoryStore()
    store.upsert({'name': 'test', 'description': 'hello'})
    results = store.recall(query='hello')
"""

import math
from datetime import datetime, timezone

from neo4j import GraphDatabase

import json as _json

from memoryschema.config import ALL_RELATION_TYPES as _RELATION_TYPES
from memoryschema.tags import observation_text
from memoryschema.hierarchy import project_matches_scope


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


_LUCENE_SPECIAL = set(r'+-&|!(){}[]^"~*?:\/')


def _lucene_escape(query):
    """Backslash-escape Lucene query-syntax metacharacters.

    `db.index.fulltext.queryNodes` parses its argument as a Lucene query, so a
    raw user string with '/', ':', unbalanced quotes/parens, etc. throws a
    ClientError that crashes the CLI — and these are routine in a trading journal
    ('USD/JPY', 'R/R', 'win/loss'). Escaping turns the query into a safe literal
    term search, matching the command's documented substring/keyword intent.
    """
    out = []
    for ch in str(query):
        if ch in _LUCENE_SPECIAL:
            out.append("\\")
        out.append(ch)
    return "".join(out)


def connect(config=None, uri=None, user=None, password=None):
    """Build a Neo4j driver, run a RETURN 1 liveness probe, and wrap auth failures with a friendly
    ConnectionError. The SINGLE place driver construction + the probe live — the store, schema setup,
    migration, and preflight all route through this instead of re-implementing it.
    """
    if config is None and uri is None:
        from memoryschema.config import MemoryConfig
        config = MemoryConfig()
    if config is not None:
        uri = uri or config.neo4j_uri
        user = user or config.neo4j_user
        password = password or config.neo4j_password
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            session.run('RETURN 1')
    except Exception as e:
        driver.close()
        err = str(e).lower()
        if 'credentials' in err or 'unauthorized' in err or 'authentication' in err:
            raise ConnectionError(
                f"Neo4j auth failed at {uri}. Set NEO4J_PASSWORD env var or check "
                f"memoryschema.toml [neo4j] section.") from e
        raise
    return driver


def _neo4j_serialize_obs(obs):
    """Serialize observation for Neo4j list property. Plain string."""
    if isinstance(obs, dict):
        return obs.get('text', str(obs))
    return str(obs)


def _neo4j_deserialize_obs(raw):
    """Deserialize observation from Neo4j list property.

    Plain strings or legacy JSON strings → plain string.
    """
    if isinstance(raw, str) and raw.startswith('{"t":'):
        try:
            d = _json.loads(raw)
            return d.get('t', d.get('text', str(raw)))
        except (ValueError, KeyError):
            pass
    return str(raw)


# Non-default embedding spaces, mirroring spaces.get_registry() minus 'default'.
# Each is stored as its own native float-array property `emb_<space>`; the
# 'default' vector stays in m.embedding (for the memory_embedding vector index).
_FIELD_SPACES = ('name', 'description', 'observations', 'prompt', 'reasoning', 'chain')


def _serialize_multispace(memory_dict):
    """Return Neo4j props for an entry's multi-space data, or None to leave props untouched.

    Per-space native float arrays (`emb_<space>`) for non-default spaces. Absent field
    spaces are set to None so a re-upsert clears stale per-space props (in Cypher,
    SET m += {k: null} removes the property). `divergence_profile` is stored as a JSON
    string. Returns None when the entry carries no 'embeddings' (e.g. legacy/metadata-only
    upsert) so existing per-space props are preserved.
    """
    embeddings = memory_dict.get('embeddings')
    if not embeddings:
        return None
    props = {}
    for space in _FIELD_SPACES:
        props['emb_' + space] = embeddings.get(space)  # vector, or None to clear stale
    div = memory_dict.get('divergence_profile')
    props['divergence_profile_json'] = _json.dumps(div) if div else None
    return props


def _deserialize_multispace(d):
    """Reconstruct d['embeddings'] + d['divergence_profile'] from node props in place,
    stripping the raw emb_<space>/divergence_profile_json keys so they don't leak.

    'default' is reconstructed from d['embedding']. A multi-space dict is only exposed
    when at least one field space is present; default-only entries keep the single
    'embedding' fallback path.
    """
    embeddings = {}
    default_vec = d.get('embedding')
    if default_vec:
        embeddings['default'] = default_vec
    for space in _FIELD_SPACES:
        vec = d.pop('emb_' + space, None)
        if vec:
            embeddings[space] = vec
    div_json = d.pop('divergence_profile_json', None)
    # Expose the multi-space dict whenever any non-default field space is present (matches the
    # docstring); default-only entries keep the single-'embedding' fallback path.
    if any(space != 'default' for space in embeddings):
        d['embeddings'] = embeddings
        if div_json:
            try:
                d['divergence_profile'] = _json.loads(div_json)
            except (ValueError, TypeError):
                pass
    return d


class Neo4jMemoryStore:
    """Neo4j-backed memory store with the same interface as MemoryStore."""

    def __init__(self, uri=None, user=None, password=None, config=None):
        """Initialize Neo4j connection.

        Args:
            uri: Bolt URI. Defaults via MemoryConfig.
            user: Username. Defaults via MemoryConfig.
            password: Password. Defaults via MemoryConfig.
            config: Optional MemoryConfig instance (overrides individual params).
        """
        if config is None and uri is None:
            from memoryschema.config import MemoryConfig
            config = MemoryConfig()
        self.config = config  # retained for tunable scoring weights
        self._driver = connect(config=config, uri=uri, user=user, password=password)

    def close(self):
        self._driver.close()

    # --- Core CRUD ---

    def upsert(self, memory_dict):
        """Insert or merge a memory entry. O(1) in Neo4j."""
        name = memory_dict.get('name')
        if not name:
            return None

        now = _now_iso()

        # Mutable props (applied on both CREATE and MATCH). Includes the
        # lifecycle/temporal fields — set_lifecycle + re-index updates an
        # EXISTING node, so omitting them here drops them from Neo4j entirely.
        props = {}
        for key in ('schema', 'type', 'status', 'description',
                     'importance', 'body', 'filepath', 'prompt',
                     'reasoning', 'project',
                     'key', 'valid_from', 'superseded_at', 'superseded_by',
                     'promoted_to'):
            if key in memory_dict and memory_dict[key] is not None:
                props[key] = memory_dict[key]

        # Immutable props (applied on CREATE only)

        raw_observations = memory_dict.get('observations', [])
        # Serialize observations for Neo4j
        neo4j_obs = [_neo4j_serialize_obs(o) for o in raw_observations]
        # observations_text stays plain text for fulltext search
        obs_text = ' '.join(observation_text(o) for o in raw_observations)
        embedding = memory_dict.get('embedding')

        # Set verified_at if any measured observation present


        with self._driver.session() as session:
            session.run("""
                MERGE (m:Memory {name: $name})
                ON CREATE SET
                    m += $props,
                    m.observations = $observations,
                    m.observations_text = $observations_text,
                    m.created_at = $now,
                    m.last_accessed = $now,
                    m.access_count = 0
                ON MATCH SET
                    m += $props,
                    m.last_accessed = $now
                WITH m
                WITH m, coalesce(m.observations, []) AS existing
                WITH m, existing, [x IN $observations WHERE NOT x IN existing] AS new_obs
                SET m.observations = existing + new_obs,
                    m.observations_text = reduce(s = '', x IN (existing + new_obs) |
                        CASE WHEN x STARTS WITH '{"t":' THEN s
                        ELSE s + ' ' + x END)
                RETURN m
            """, name=name, props=props,
                observations=neo4j_obs,
                observations_text=obs_text, now=now)

            if embedding:
                session.run("""
                    MATCH (m:Memory {name: $name})
                    SET m.embedding = $embedding
                """, name=name, embedding=embedding)

            # Multi-space embeddings (per-space float arrays) + divergence profile.
            # set-or-clear across the fixed field-space set so re-upserts don't leave
            # stale per-space props (SET m += {k: null} removes the property).
            multispace = _serialize_multispace(memory_dict)
            if multispace is not None:
                session.run("""
                    MATCH (m:Memory {name: $name})
                    SET m += $multispace
                """, name=name, multispace=multispace)

            relations = memory_dict.get('relations', [])
            for rel in relations:
                target = rel.get('target')
                rel_type = rel.get('type')
                if not (target and rel_type and target != name):
                    continue
                # SECURITY: Neo4j does not support parameterized relationship
                # types. The allowlist check below is the security boundary —
                # rel_type is interpolated into the Cypher query via f-string.
                if rel_type not in _RELATION_TYPES:
                    raise ValueError(
                        f"Invalid relation type {rel_type!r}, "
                        f"must be one of: {', '.join(sorted(_RELATION_TYPES))}"
                    )
                # SUPERSEDES → R7 cycle detection BEFORE creating the edge, so a cycle is REJECTED with
                # the graph left CLEAN (matching the JSONL store's pre-write check) — not persisted and then
                # reported. Order-independent: the query searches for a PRE-EXISTING path t -[:SUPERSEDES*]-> s,
                # which by construction never contains the not-yet-created s -> t edge, so checking before vs
                # after the MERGE returns the identical answer.
                if rel_type == 'SUPERSEDES':
                    cycle = session.run("""
                        OPTIONAL MATCH path = (t:Memory {name: $target})
                            -[:SUPERSEDES*]->(s:Memory {name: $source})
                        RETURN path IS NOT NULL AS has_cycle
                    """, source=name, target=target).single()
                    if cycle and cycle['has_cycle']:
                        raise ValueError(
                            f"SUPERSEDES cycle detected: {name} → {target} "
                            f"would create a circular chain")

                session.run(f"""
                    MATCH (s:Memory {{name: $source}})
                    MERGE (t:Memory {{name: $target}})
                    MERGE (s)-[r:{rel_type}]->(t)
                """, source=name, target=target)

                # SUPERSEDES → mark the (now-superseded) target
                if rel_type == 'SUPERSEDES':
                    session.run("""
                        MATCH (t:Memory {name: $target})
                        WHERE t.status IS NULL OR t.status = 'active'
                        SET t.status = 'superseded'
                    """, target=target)

                # CONTRADICTS → ensure symmetric edge
                if rel_type == 'CONTRADICTS':
                    session.run("""
                        MATCH (s:Memory {name: $source}), (t:Memory {name: $target})
                        MERGE (t)-[:CONTRADICTS]->(s)
                    """, source=name, target=target)

        return self.get(name)

    def get(self, name):
        """Look up by name. No side effects."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {name: $name})
                OPTIONAL MATCH (m)-[r]->(target:Memory)
                WHERE type(r) IN $rel_types
                WITH m, collect({target: target.name, type: type(r)}) AS relations
                OPTIONAL MATCH (source:Memory)-[bl]->(m)
                WHERE type(bl) IN $rel_types
                WITH m, relations, collect({source: source.name, type: type(bl)}) AS backlinks
                OPTIONAL MATCH (m)-[a:ASSOCIATED_WITH]->(assoc:Memory)
                WITH m, relations, backlinks,
                     collect({name: assoc.name, score: a.score}) AS associations
                RETURN m, relations, backlinks, associations
            """, name=name, rel_types=list(_RELATION_TYPES))
            record = result.single()
            if not record:
                return None
            return self._record_to_dict(record)

    def access(self, name):
        """Cognitive read — increment access_count, update last_accessed."""
        with self._driver.session() as session:
            session.run("""
                MATCH (m:Memory {name: $name})
                SET m.access_count = m.access_count + 1,
                    m.last_accessed = $now
            """, name=name, now=_now_iso())
        return self.get(name)

    def exists(self, name):
        with self._driver.session() as session:
            result = session.run(
                "MATCH (m:Memory {name: $name}) RETURN count(m) > 0 AS exists",
                name=name)
            return result.single()['exists']

    def count(self):
        with self._driver.session() as session:
            result = session.run("MATCH (m:Memory) RETURN count(m) AS n")
            return result.single()['n']

    def delete(self, name):
        with self._driver.session() as session:
            result = session.run(
                "MATCH (m:Memory {name: $name}) DETACH DELETE m RETURN count(m) AS deleted",
                name=name)
            return result.single()['deleted'] > 0

    def archive(self, name):
        """Set a memory's status to archived."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {name: $name})
                SET m.status = 'archived'
                RETURN count(m) AS n
            """, name=name)
            return result.single()['n'] > 0

    def unarchive(self, name):
        """Set an archived memory back to active."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {name: $name})
                WHERE m.status = 'archived'
                SET m.status = 'active'
                RETURN count(m) AS n
            """, name=name)
            return result.single()['n'] > 0

    def reactivate(self, name):
        """Set a superseded memory back to active."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {name: $name})
                WHERE m.status = 'superseded'
                SET m.status = 'active'
                RETURN count(m) AS n
            """, name=name)
            return result.single()['n'] > 0

    def release_quarantine(self, name):
        """Set a quarantined memory back to active."""
        with self._driver.session() as session:
            result = session.run("""
                MATCH (m:Memory {name: $name})
                WHERE m.status = 'quarantined'
                SET m.status = 'active'
                RETURN count(m) AS n
            """, name=name)
            return result.single()['n'] > 0

    def list_all(self, project=None, include_inactive=False):
        # Collect relations, backlinks, and associations per node (mirrors get())
        # so downstream consumers — the `associations` CLI and `migrate
        # neo4j-to-jsonl` — see the full graph, not bare nodes.
        rel_types = list(_RELATION_TYPES)
        tail = """
                OPTIONAL MATCH (m)-[r]->(target:Memory)
                WHERE type(r) IN $rel_types
                WITH m, collect({target: target.name, type: type(r)}) AS relations
                OPTIONAL MATCH (source:Memory)-[bl]->(m)
                WHERE type(bl) IN $rel_types
                WITH m, relations, collect({source: source.name, type: type(bl)}) AS backlinks
                OPTIONAL MATCH (m)-[a:ASSOCIATED_WITH]->(assoc:Memory)
                WITH m, relations, backlinks,
                     collect({name: assoc.name, score: a.score}) AS associations
                RETURN m, relations, backlinks, associations
        """
        with self._driver.session() as session:
            status_clause = "" if include_inactive else \
                " AND (m.status IS NULL OR m.status = 'active')"
            if project is not None:
                result = session.run(f"""
                    MATCH (m:Memory)
                    WHERE (m.project IS NULL
                       OR m.project = $project
                       OR m.project STARTS WITH $project_prefix){status_clause}
                    {tail}
                """, project=project, project_prefix=project + '.', rel_types=rel_types)
            else:
                where = "WHERE m.status IS NULL OR m.status = 'active'" \
                    if not include_inactive else ""
                result = session.run(f"MATCH (m:Memory) {where} {tail}",
                                     rel_types=rel_types)
            return [self._record_to_dict(r) for r in result]

    # --- Search ---

    def search(self, query=None, type=None, project=None, limit=10,
               include_inactive=False):
        """Text search across name, description, observations, prompt, reasoning."""
        with self._driver.session() as session:
            active_filter = "" if include_inactive else \
                " AND (node.status IS NULL OR node.status = 'active')"
            if query:
                result = session.run(f"""
                    CALL db.index.fulltext.queryNodes('memory_fulltext', $search_query)
                    YIELD node, score
                    WHERE ($filter_type IS NULL OR node.type = $filter_type)
                      AND ($filter_project IS NULL
                           OR node.project IS NULL
                           OR node.project = $filter_project
                           OR node.project STARTS WITH $filter_project_prefix){active_filter}
                    RETURN node
                    LIMIT $result_limit
                """, search_query=_lucene_escape(query), filter_type=type,
                    filter_project=project,
                    filter_project_prefix=(project + '.') if project else None,
                    result_limit=limit)
            else:
                clauses = ["MATCH (m:Memory)"]
                wheres = []
                if not include_inactive:
                    wheres.append("(m.status IS NULL OR m.status = 'active')")
                if type:
                    wheres.append("m.type = $filter_type")
                if project:
                    wheres.append("(m.project IS NULL OR m.project = $filter_project OR m.project STARTS WITH $filter_project_prefix)")
                if wheres:
                    clauses.append("WHERE " + " AND ".join(wheres))
                clauses.append("RETURN m AS node LIMIT $result_limit")
                result = session.run(' '.join(clauses),
                                     filter_type=type, filter_project=project,
                                     filter_project_prefix=(project + '.') if project else None,
                                     result_limit=limit)
            return [self._node_to_dict(r.get('node') or r.get('m')) for r in result]

    # --- Recall ---

    def recall(self, query=None, name=None, depth=2, decay=0.8, limit=10,
               project=None, include_inactive=False, max_inherit_depth=3):
        """Cascade recall with spreading activation via Neo4j.

        If project is set, scopes traversal to the project hierarchy
        (bidirectional: child sees parent, parent sees child).
        Excludes non-active entries from results unless include_inactive=True.
        Non-active entries remain traversable in BFS (traversable-not-returned).
        """
        query_embedding = None
        if query:
            try:
                from memoryschema.embeddings import embed_text
                query_embedding = embed_text(query)
            except Exception:
                pass

        seeds = []
        if name:
            entry = self.get(name)
            if entry:
                seeds = [entry]
        elif query and query_embedding:
            n_seed = self.config.seed_count if self.config else 3
            seeds = self._vector_search(query_embedding, top_k=n_seed, project=project)
        else:
            return []

        # Filter seeds to active only (unless include_inactive)
        if not include_inactive:
            seeds = [s for s in seeds
                     if s.get('status', 'active') == 'active']

        if not seeds:
            return []

        visited = {}
        # Per-hop frontier BFS: expand a WHOLE hop level in ONE batched neighbor fetch (replaces the
        # old per-node N+1 cascade). Each frontier node carries its OWN max score; `visited` keeps the
        # global max. Semantics-preserving vs the prior FIFO+re-queue form (verified identical results).
        frontier = {}  # name -> (entry, score); expand once per hop at the best score seen for it
        for seed in seeds:
            seed_score = self._score_entry(seed, query_embedding)
            if query:
                searchable = self._searchable_text(seed)
                if query.lower() in searchable:
                    seed_score = min(seed_score + 0.1, 1.0)

            result = {
                'name': seed['name'],
                'score': round(seed_score, 4),
                'hop': 0,
                'channel': 'seed',
                'type': seed.get('type'),
                'importance': seed.get('importance'),
                'description': seed.get('description'),
                'observations': seed.get('observations', []),
                'status': seed.get('status', 'active'),
                'project': seed.get('project'),
            }
            if seed['name'] not in visited or result['score'] > visited[seed['name']]['score']:
                visited[seed['name']] = result
            prev = frontier.get(seed['name'])
            if prev is None or seed_score > prev[1]:
                frontier[seed['name']] = (seed, seed_score)

        for _hop in range(depth):
            if not frontier:
                break
            next_hop = _hop + 1
            neighbors_by_src = self._get_neighbors_batch(list(frontier), project=project)
            next_frontier = {}
            for src_name, (current, current_score) in frontier.items():
                hop_score = current_score * decay
                for neighbor_info in neighbors_by_src.get(src_name, []):
                    neighbor = neighbor_info['entry']
                    channel = neighbor_info['channel']

                    if channel == 'association':
                        n_score = hop_score * neighbor_info.get('assoc_score', 0.5)
                    else:
                        n_score = hop_score * self._score_entry(neighbor, query_embedding)

                    result = {
                        'name': neighbor['name'],
                        'score': round(n_score, 4),
                        'hop': next_hop,
                        'channel': channel,
                        'type': neighbor.get('type'),
                        'importance': neighbor.get('importance'),
                        'description': neighbor.get('description'),
                        'observations': neighbor.get('observations', []),
                        'status': neighbor.get('status', 'active'),
                        'project': neighbor.get('project'),
                    }
                    if channel in ('relation', 'backlink'):
                        result['relation_type'] = neighbor_info.get('rel_type')

                    nname = neighbor['name']
                    if nname not in visited or result['score'] > visited[nname]['score']:
                        visited[nname] = result
                        prev = next_frontier.get(nname)
                        if prev is None or n_score > prev[1]:
                            next_frontier[nname] = (neighbor, n_score)
            frontier = next_frontier

        # Filter to active entries unless include_inactive (traversable-not-returned)
        if not include_inactive:
            results = sorted(
                [r for r in visited.values()
                 if r.get('status', 'active') == 'active'],
                key=lambda x: x['score'], reverse=True)
        else:
            results = sorted(visited.values(), key=lambda x: x['score'], reverse=True)

        # Post-filter: enforce max_inherit_depth (Cypher uses STARTS WITH
        # which doesn't respect depth limits — apply Python-side)
        if project is not None and max_inherit_depth is not None:
            results = [r for r in results
                       if project_matches_scope(
                           r.get('project') or '', project,
                           max_depth=max_inherit_depth)]

        return results[:limit]

    # --- Associations ---

    def compute_backlinks(self, project=None):
        """Backlinks are implicit in Neo4j — count nodes with incoming relations."""
        with self._driver.session() as session:
            if project is not None:
                result = session.run("""
                    MATCH (m:Memory)<-[r]-(s:Memory)
                    WHERE type(r) IN $rel_types
                      AND (m.project = $project OR m.project STARTS WITH $project_prefix)
                      AND (s.project = $project OR s.project STARTS WITH $project_prefix)
                    WITH m, count(r) AS bl
                    WHERE bl > 0
                    RETURN count(m) AS n
                """, rel_types=list(_RELATION_TYPES),
                    project=project, project_prefix=project + '.')
            else:
                result = session.run("""
                    MATCH (m:Memory)<-[r]-(:Memory)
                    WHERE type(r) IN $rel_types
                    WITH m, count(r) AS bl
                    WHERE bl > 0
                    RETURN count(m) AS n
                """, rel_types=list(_RELATION_TYPES))
            return result.single()['n']

    def compute_associations(self, k=10, project=None):
        """Compute k-NN associations using vector index."""
        with self._driver.session() as session:
            if project is not None:
                result = session.run("""
                    MATCH (m:Memory)
                    WHERE m.embedding IS NOT NULL
                      AND (m.project = $project OR m.project STARTS WITH $project_prefix)
                    RETURN m.name AS name
                """, project=project, project_prefix=project + '.')
            else:
                result = session.run("""
                    MATCH (m:Memory)
                    WHERE m.embedding IS NOT NULL
                    RETURN m.name AS name
                """)
            names = [r['name'] for r in result]

            if len(names) < 2:
                return 0

            session.run("MATCH ()-[a:ASSOCIATED_WITH]->() DELETE a")

            count = 0
            for i, name in enumerate(names):
                session.run("""
                    MATCH (m:Memory {name: $name})
                    WHERE m.embedding IS NOT NULL
                    CALL db.index.vector.queryNodes('memory_embedding', $k_plus, m.embedding)
                    YIELD node AS neighbor, score
                    WHERE neighbor <> m
                    WITH m, neighbor, score
                    ORDER BY score DESC
                    LIMIT $k
                    MERGE (m)-[a:ASSOCIATED_WITH]->(neighbor)
                    SET a.score = score
                """, name=name, k=k, k_plus=k + 1)
                count += 1
                if (i + 1) % 500 == 0:
                    print(f'  Associations: {i + 1}/{len(names)}...')

            return count

    def compute_associations_single(self, name, k=10):
        """Compute k-NN for a single node only. For hook use."""
        with self._driver.session() as session:
            session.run("""
                MATCH (m:Memory {name: $name})-[a:ASSOCIATED_WITH]->()
                DELETE a
            """, name=name)

            session.run("""
                MATCH (m:Memory {name: $name})
                WHERE m.embedding IS NOT NULL
                CALL db.index.vector.queryNodes('memory_embedding', $k_plus, m.embedding)
                YIELD node AS neighbor, score
                WHERE neighbor <> m
                WITH m, neighbor, score
                ORDER BY score DESC
                LIMIT $k
                MERGE (m)-[a:ASSOCIATED_WITH]->(neighbor)
                SET a.score = score
            """, name=name, k=k, k_plus=k + 1)

    # --- Internal helpers ---

    def _vector_search(self, query_embedding, top_k=10, project=None):
        with self._driver.session() as session:
            if project is not None:
                # Over-fetch and post-filter with iterative widening
                # Try 3x, 9x, then 100x if post-filter yields < top_k
                entries = []
                for multiplier in (3, 9, 100):
                    oversample = top_k * multiplier
                    result = session.run("""
                        CALL db.index.vector.queryNodes('memory_embedding', $oversample, $embedding)
                        YIELD node, score
                        WHERE node.project IS NULL
                           OR node.project = $project
                           OR node.project STARTS WITH $project_prefix
                           OR $project STARTS WITH (node.project + '.')
                        RETURN node, score
                        LIMIT $top_k
                    """, embedding=query_embedding, top_k=top_k,
                        oversample=oversample, project=project,
                        project_prefix=project + '.')
                    entries = []
                    for r in result:
                        entry = self._node_to_dict(r['node'])
                        entry['_vector_score'] = r['score']
                        entries.append(entry)
                    if len(entries) >= top_k:
                        break  # Got enough results
                return entries
            else:
                result = session.run("""
                    CALL db.index.vector.queryNodes('memory_embedding', $top_k, $embedding)
                    YIELD node, score
                    RETURN node, score
                """, embedding=query_embedding, top_k=top_k)
                entries = []
                for r in result:
                    entry = self._node_to_dict(r['node'])
                    entry['_vector_score'] = r['score']
                    entries.append(entry)
                return entries

    def _get_neighbors_batch(self, names, project=None):
        """Neighbors for a WHOLE frontier in ONE round-trip (vs _get_neighbors per node — the recall
        N+1 cascade). Returns {src_name: [neighbor_info, ...]} with the SAME neighbor_info shape as
        _get_neighbors (channel relation/backlink carry rel_type; association carries assoc_score).
        """
        out = {n: [] for n in names}
        if not names:
            return out
        scope_clause = ""
        assoc_scope = ""
        params = {'names': list(names), 'rel_types': list(_RELATION_TYPES)}
        if project is not None:
            scope_clause = """
                AND (n.project IS NULL
                     OR n.project = $scope_project
                     OR n.project STARTS WITH $scope_prefix
                     OR $scope_project STARTS WITH (n.project + '.'))"""
            assoc_scope = """
                AND (an.project = $scope_project
                     OR an.project STARTS WITH $scope_prefix
                     OR $scope_project STARTS WITH (an.project + '.'))"""
            params['scope_project'] = project
            params['scope_prefix'] = project + '.'

        # ONE UNWIND over the frontier; a scoped CALL subquery unions the three channels PER SOURCE
        # (so neighbor order — hence tie-break stability — matches the per-node original). Relation/
        # backlink rows return the full node (needed by _score_entry's multi-space relevance).
        # ASSOCIATION rows return n=null + only the scalar fields used downstream: their embeddings are
        # NEVER read (scored by a.score), so we avoid dragging the per-space arrays over bolt and
        # deserializing them — the dominant recall cost (~64% of neighbors are associations).
        cypher = f"""
            UNWIND $names AS src
            MATCH (m:Memory {{name: src}})
            CALL (m) {{
                MATCH (m)-[r]->(n:Memory)
                WHERE type(r) IN $rel_types{scope_clause}
                RETURN n AS n, 'relation' AS channel, type(r) AS rel_type, null AS assoc,
                       null AS aname, null AS atype, null AS aimp, null AS adesc,
                       null AS aobs, null AS astatus, null AS aproj
              UNION
                MATCH (n:Memory)-[r]->(m)
                WHERE type(r) IN $rel_types{scope_clause}
                RETURN n AS n, 'backlink' AS channel, type(r) AS rel_type, null AS assoc,
                       null AS aname, null AS atype, null AS aimp, null AS adesc,
                       null AS aobs, null AS astatus, null AS aproj
              UNION
                MATCH (m)-[a:ASSOCIATED_WITH]->(an:Memory)
                WHERE true{assoc_scope}
                RETURN null AS n, 'association' AS channel, null AS rel_type, a.score AS assoc,
                       an.name AS aname, an.type AS atype, an.importance AS aimp, an.description AS adesc,
                       an.observations AS aobs, an.status AS astatus, an.project AS aproj
            }}
            RETURN src AS s, n, channel, rel_type, assoc, aname, atype, aimp, adesc, aobs, astatus, aproj
        """
        with self._driver.session() as session:
            for row in session.run(cypher, **params):
                if row['channel'] == 'association':
                    obs = row['aobs'] or []
                    entry = {
                        'name': row['aname'], 'type': row['atype'], 'importance': row['aimp'],
                        'description': row['adesc'],
                        'observations': [_neo4j_deserialize_obs(o) for o in obs],
                        'project': row['aproj'],
                    }
                    if row['astatus'] is not None:    # absent status -> result default 'active' (as before)
                        entry['status'] = row['astatus']
                    out.setdefault(row['s'], []).append(
                        {'entry': entry, 'channel': 'association', 'assoc_score': row['assoc']})
                else:
                    out.setdefault(row['s'], []).append(
                        {'entry': self._node_to_dict(row['n']),
                         'channel': row['channel'], 'rel_type': row['rel_type']})
        return out

    def _get_neighbors(self, name, project=None):
        """Single-node neighbors — thin wrapper over the batched fetch (kept for callers/tests)."""
        return self._get_neighbors_batch([name], project=project).get(name, [])

    def _score_entry(self, entry, query_embedding=None, mode='semantic'):
        recency = 0.5
        last = entry.get('last_accessed') or entry.get('created_at')
        if last:
            try:
                accessed = datetime.fromisoformat(last)
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                hours = max(0, (now - accessed).total_seconds() / 3600)
                decay = self.config.recency_decay if self.config else 0.995
                recency = decay ** hours
            except (ValueError, TypeError):
                pass

        # Type-dependent recency modifier
        entry_type = entry.get('type', 'semantic')
        if entry_type == 'semantic':
            recency = max(recency, 0.6)
        elif entry_type == 'procedural':
            access_count = min(entry.get('access_count') or 0, 10)
            exponent = 1.0 / (1.0 + 0.3 * access_count)
            recency = recency ** exponent
        # episodic: standard decay (no modification)

        importance = entry.get('importance', 5)
        if importance is None:
            importance = 5
        importance = importance / 10.0

        relevance = 0.0
        if query_embedding and (entry.get('embeddings') or entry.get('embedding')):
            # Variance-weighted multi-space relevance (shared with the JSONL store).
            # Falls back to the single 'embedding' vector for legacy/default-only entries.
            from memoryschema.store import multi_space_relevance
            relevance = multi_space_relevance(entry, query_embedding)
        elif entry.get('_vector_score') is not None:
            relevance = entry['_vector_score']

        from memoryschema.store import _resolve_weights
        w_r, w_i, w_v = _resolve_weights(getattr(self, 'config', None), mode)

        if not query_embedding and entry.get('_vector_score') is None:
            w_r += w_v * 0.4
            w_i += w_v * 0.6
            w_v = 0.0

        score = recency * w_r + importance * w_i + relevance * w_v

        # Hub bonus: log-scale to prevent rich-get-richer compounding
        backlinks = len(entry.get('backlinks', []))
        if backlinks > 0:
            score += 0.05 * math.log(1 + backlinks)

        # Confidence is write-time metadata only — not a scoring input.

        # MITIGATES dampening
        mitigates_count = sum(
            1 for bl in entry.get('backlinks', [])
            if bl.get('type') == 'MITIGATES'
        )
        if mitigates_count > 0:
            score *= self.config.mitigation_dampening if self.config else 0.95

        return round(min(score, 1.0), 4)

    def _searchable_text(self, entry):
        return ' '.join([
            entry.get('name', ''),
            entry.get('description', ''),
            ' '.join(entry.get('observations', [])),
            entry.get('prompt', '') or '',
            entry.get('reasoning', '') or '',
        ]).lower()

    def _node_to_dict(self, node):
        d = dict(node)
        if 'observations' not in d or d['observations'] is None:
            d['observations'] = []
        else:
            d['observations'] = [_neo4j_deserialize_obs(o) for o in d['observations']]
        d.pop('observations_text', None)
        d.setdefault('relations', [])
        d.setdefault('backlinks', [])
        d.setdefault('associations', [])
        _deserialize_multispace(d)
        return d

    def _record_to_dict(self, record):
        d = self._node_to_dict(record['m'])
        d['relations'] = [r for r in record['relations'] if r.get('target')]
        d['backlinks'] = [b for b in record['backlinks'] if b.get('source')]
        d['associations'] = [a for a in record['associations'] if a.get('name')]
        return d


def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
