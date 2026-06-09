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

from datetime import datetime, timezone

from neo4j import GraphDatabase

from memoryschema.config import ALL_RELATION_TYPES as _RELATION_TYPES


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


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
        if config:
            uri = uri or config.neo4j_uri
            user = user or config.neo4j_user
            password = password or config.neo4j_password

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        with self._driver.session() as session:
            session.run('RETURN 1')

    def close(self):
        self._driver.close()

    # --- Core CRUD ---

    def upsert(self, memory_dict):
        """Insert or merge a memory entry. O(1) in Neo4j."""
        name = memory_dict.get('name')
        if not name:
            return None

        now = _now_iso()

        props = {}
        for key in ('schema', 'type', 'description', 'importance',
                     'body', 'source', 'filepath', 'prompt', 'reasoning', 'project'):
            if key in memory_dict and memory_dict[key] is not None:
                props[key] = memory_dict[key]

        observations = memory_dict.get('observations', [])
        embedding = memory_dict.get('embedding')

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
                WITH m, m.observations AS existing
                WITH m, existing, [x IN $observations WHERE NOT x IN existing] AS new_obs
                SET m.observations = existing + new_obs,
                    m.observations_text = reduce(s = '', x IN (existing + new_obs) | s + ' ' + x)
                RETURN m
            """, name=name, props=props, observations=observations,
                observations_text=' '.join(observations), now=now)

            if embedding:
                session.run("""
                    MATCH (m:Memory {name: $name})
                    SET m.embedding = $embedding
                """, name=name, embedding=embedding)

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
                session.run(f"""
                    MATCH (s:Memory {{name: $source}})
                    MERGE (t:Memory {{name: $target}})
                    MERGE (s)-[r:{rel_type}]->(t)
                """, source=name, target=target)

                # SUPERSEDES → mark target as superseded
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

    def list_all(self, project=None):
        with self._driver.session() as session:
            if project is not None:
                result = session.run("""
                    MATCH (m:Memory)
                    WHERE m.project IS NULL
                       OR m.project = $project
                       OR m.project STARTS WITH $project_prefix
                    RETURN m
                """, project=project, project_prefix=project + '.')
            else:
                result = session.run("MATCH (m:Memory) RETURN m")
            return [self._node_to_dict(r['m']) for r in result]

    # --- Search ---

    def search(self, query=None, type=None, project=None, limit=10):
        """Text search across name, description, observations, prompt, reasoning."""
        with self._driver.session() as session:
            if query:
                result = session.run("""
                    CALL db.index.fulltext.queryNodes('memory_fulltext', $search_query)
                    YIELD node, score
                    WHERE ($filter_type IS NULL OR node.type = $filter_type)
                      AND ($filter_project IS NULL
                           OR node.project IS NULL
                           OR node.project = $filter_project
                           OR node.project STARTS WITH $filter_project_prefix)
                    RETURN node
                    LIMIT $result_limit
                """, search_query=query, filter_type=type,
                    filter_project=project,
                    filter_project_prefix=(project + '.') if project else None,
                    result_limit=limit)
            else:
                clauses = ["MATCH (m:Memory)"]
                wheres = []
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

    def recall(self, query=None, name=None, depth=2, decay=0.8, limit=10, project=None):
        """Cascade recall with spreading activation via Neo4j.

        If project is set, scopes traversal to the project hierarchy
        (bidirectional: child sees parent, parent sees child).
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
            seeds = self._vector_search(query_embedding, top_k=3, project=project)
        else:
            return []

        if not seeds:
            return []

        visited = {}
        queue = []

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
            }
            if seed['name'] not in visited or result['score'] > visited[seed['name']]['score']:
                visited[seed['name']] = result
            queue.append((seed, seed_score, 0))

        while queue:
            current, current_score, current_hop = queue.pop(0)
            if current_hop >= depth:
                continue

            next_hop = current_hop + 1
            hop_score = current_score * decay

            neighbors = self._get_neighbors(current['name'], project=project)

            for neighbor_info in neighbors:
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
                }
                if channel in ('relation', 'backlink'):
                    result['relation_type'] = neighbor_info.get('rel_type')

                if neighbor['name'] not in visited or result['score'] > visited[neighbor['name']]['score']:
                    visited[neighbor['name']] = result
                    queue.append((neighbor, n_score, next_hop))

        results = sorted(visited.values(), key=lambda x: x['score'], reverse=True)
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

    def _get_neighbors(self, name, project=None):
        neighbors = []
        scope_clause = ""
        scope_params = {}
        if project is not None:
            scope_clause = """
                AND (n.project IS NULL
                     OR n.project = $scope_project
                     OR n.project STARTS WITH $scope_prefix
                     OR $scope_project STARTS WITH (n.project + '.'))"""
            scope_params = {'scope_project': project, 'scope_prefix': project + '.'}

        with self._driver.session() as session:
            result = session.run(f"""
                MATCH (m:Memory {{name: $name}})-[r]->(n:Memory)
                WHERE type(r) IN $rel_types{scope_clause}
                RETURN n, type(r) AS rel_type
            """, name=name, rel_types=list(_RELATION_TYPES), **scope_params)
            for r in result:
                neighbors.append({
                    'entry': self._node_to_dict(r['n']),
                    'channel': 'relation',
                    'rel_type': r['rel_type'],
                })

            result = session.run(f"""
                MATCH (n:Memory)-[r]->(m:Memory {{name: $name}})
                WHERE type(r) IN $rel_types{scope_clause}
                RETURN n, type(r) AS rel_type
            """, name=name, rel_types=list(_RELATION_TYPES), **scope_params)
            for r in result:
                neighbors.append({
                    'entry': self._node_to_dict(r['n']),
                    'channel': 'backlink',
                    'rel_type': r['rel_type'],
                })

            assoc_scope = ""
            if project is not None:
                assoc_scope = """
                    AND (n.project = $scope_project
                         OR n.project STARTS WITH $scope_prefix
                         OR $scope_project STARTS WITH (n.project + '.'))"""
            result = session.run(f"""
                MATCH (m:Memory {{name: $name}})-[a:ASSOCIATED_WITH]->(n:Memory)
                WHERE true{assoc_scope}
                RETURN n, a.score AS score
            """, name=name, **scope_params)
            for r in result:
                neighbors.append({
                    'entry': self._node_to_dict(r['n']),
                    'channel': 'association',
                    'assoc_score': r['score'],
                })

        return neighbors

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
                recency = 0.995 ** hours
            except (ValueError, TypeError):
                pass

        importance = entry.get('importance', 5)
        if importance is None:
            importance = 5
        importance = importance / 10.0

        relevance = 0.0
        if query_embedding and entry.get('embedding'):
            relevance = max(0.0, _cosine_similarity(query_embedding, entry['embedding']))
        elif entry.get('_vector_score') is not None:
            relevance = entry['_vector_score']

        if mode == 'structured':
            w_r, w_i, w_v = 0.3, 0.5, 0.2
        else:
            w_r, w_i, w_v = 0.2, 0.3, 0.5

        if not query_embedding and entry.get('_vector_score') is None:
            w_r += w_v * 0.4
            w_i += w_v * 0.6
            w_v = 0.0

        score = recency * w_r + importance * w_i + relevance * w_v

        backlinks = len(entry.get('backlinks', []))
        if backlinks > 0:
            score += 0.05 * min(backlinks, 5)

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
            d['observations'] = list(d['observations'])
        d.pop('observations_text', None)
        d.setdefault('relations', [])
        d.setdefault('backlinks', [])
        d.setdefault('associations', [])
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
