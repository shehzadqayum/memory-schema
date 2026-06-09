"""
JSONL structured store for memory entities (L1b).

Pure Python, zero external dependencies (stdlib only).
One JSON object per line. Atomic writes via temp file + os.replace.
Optional numpy for vectorized scoring (graceful fallback).

Usage:
    from memoryschema import MemoryStore, get_store
    store = get_store()  # Neo4j if available, JSONL fallback
    store.upsert({'name': 'my-memory', 'type': 'semantic', ...})
    result = store.get('my-memory')
"""

import json
import os
import tempfile
from datetime import datetime, timezone

from memoryschema.hierarchy import project_matches_filter, project_matches_scope


def _now_iso():
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    """JSONL-backed memory store with upsert, query, and access tracking."""

    def __init__(self, jsonl_path):
        """Initialize store with path to JSONL file.

        The file is not created until the first write operation.
        """
        self._path = jsonl_path
        self._cache = None
        self._cache_mtime = None

    def _load(self):
        """Load all entries from the JSONL file.

        Returns cached entries if the file hasn't changed since last load.
        Skips malformed lines (resilience).
        """
        if not os.path.exists(self._path):
            return []

        mtime = os.path.getmtime(self._path)
        if self._cache is not None and self._cache_mtime == mtime:
            return self._cache

        entries = []
        with open(self._path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self._cache = entries
        self._cache_mtime = mtime
        return entries

    def _save(self, entries):
        """Write entries atomically to the JSONL file.

        Uses temp file + os.replace to prevent corruption.
        """
        dirpath = os.path.dirname(self._path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            suffix='.tmp', dir=dirpath if dirpath else '.',
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            os.replace(tmp_path, self._path)
            self._cache = None
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def upsert(self, memory_dict):
        """Insert or merge a memory entry.

        Insert: sets created_at, last_accessed, access_count=0.
        Merge: observations appended (exact dupes skipped),
               relations deduplicated (same target+type),
               other fields replaced, created_at preserved.

        Returns the upserted entry dict.
        """
        entries = self._load()
        name = memory_dict.get('name')
        existing = None
        for entry in entries:
            if entry.get('name') == name:
                existing = entry
                break

        now = _now_iso()

        if existing is None:
            new_entry = dict(memory_dict)
            new_entry['created_at'] = now
            new_entry['last_accessed'] = now
            new_entry['access_count'] = 0
            entries.append(new_entry)
            self._save(entries)
            return new_entry

        # Merge
        for key in ('type', 'description', 'importance', 'schema',
                     'body', 'source', 'filepath', 'prompt', 'reasoning'):
            if key in memory_dict and memory_dict[key] is not None:
                existing[key] = memory_dict[key]

        existing_obs = existing.get('observations', [])
        new_obs = memory_dict.get('observations', [])
        existing_set = set(existing_obs)
        for obs in new_obs:
            if obs not in existing_set:
                existing_obs.append(obs)
                existing_set.add(obs)
        existing['observations'] = existing_obs

        existing_rels = existing.get('relations', [])
        new_rels = memory_dict.get('relations', [])
        existing_pairs = {
            (r.get('target'), r.get('type')) for r in existing_rels
        }
        for rel in new_rels:
            pair = (rel.get('target'), rel.get('type'))
            if pair not in existing_pairs:
                existing_rels.append(rel)
                existing_pairs.add(pair)
        existing['relations'] = existing_rels

        existing['last_accessed'] = now

        self._save(entries)
        return existing

    def get(self, name):
        """Look up a memory by name. Pure read, no side effects."""
        entries = self._load()
        for entry in entries:
            if entry.get('name') == name:
                return entry
        return None

    def exists(self, name):
        """Check if a memory exists."""
        entries = self._load()
        return any(e.get('name') == name for e in entries)

    def count(self):
        """Return the number of entries."""
        return len(self._load())

    def access(self, name):
        """Cognitive read — look up and track access.

        Increments access_count and updates last_accessed.
        Returns the entry dict or None if not found.
        """
        entries = self._load()
        for entry in entries:
            if entry.get('name') == name:
                entry['access_count'] = entry.get('access_count', 0) + 1
                entry['last_accessed'] = _now_iso()
                self._save(entries)
                return entry
        return None

    def search(self, query=None, type=None, project=None, limit=10):
        """Search memories by query text, type, and/or project.

        Query does case-insensitive substring match across
        name, description, observations, prompt, reasoning, and body.
        Returns list of matching entry dicts (up to limit).
        """
        entries = self._load()
        results = []

        for entry in entries:
            if type is not None and entry.get('type') != type:
                continue
            if project is not None:
                if not project_matches_filter(entry.get('project', ''), project):
                    continue
            if query is not None:
                q = query.lower()
                searchable = ' '.join([
                    entry.get('name', ''),
                    entry.get('description', ''),
                    ' '.join(entry.get('observations', [])),
                    entry.get('body', '') or '',
                    entry.get('prompt', '') or '',
                    entry.get('reasoning', '') or '',
                ]).lower()
                if q not in searchable:
                    continue
            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def delete(self, name):
        """Delete a memory by name. Returns True if found."""
        entries = self._load()
        new_entries = [e for e in entries if e.get('name') != name]
        if len(new_entries) == len(entries):
            return False
        self._save(new_entries)
        return True

    def list_all(self, project=None):
        """Return all entries, optionally filtered to a project subtree."""
        entries = self._load()
        if project is not None:
            entries = [e for e in entries
                       if project_matches_filter(e.get('project', ''), project)]
        return entries

    def compute_backlinks(self, project=None):
        """Recompute all backlinks from relation data.

        If project is set, only compute for entries in that project subtree.
        Returns the number of entries that have backlinks.
        """
        entries = self._load()
        entry_map = {e['name']: e for e in entries if 'name' in e}

        if project is not None:
            scoped_names = {name for name, e in entry_map.items()
                           if project_matches_filter(e.get('project', ''), project)}
        else:
            scoped_names = None

        for entry in entries:
            if scoped_names is None or entry.get('name') in scoped_names:
                entry['backlinks'] = []

        for entry in entries:
            source_name = entry.get('name')
            if not source_name:
                continue
            if scoped_names is not None and source_name not in scoped_names:
                continue
            for rel in entry.get('relations', []):
                target = rel.get('target')
                rel_type = rel.get('type')
                if target and target in entry_map:
                    if scoped_names is None or target in scoped_names:
                        entry_map[target]['backlinks'].append({
                            'source': source_name,
                            'type': rel_type,
                        })

        self._save(entries)
        return sum(1 for e in entries if e.get('backlinks'))

    def compute_associations(self, k=10, project=None):
        """Compute k-nearest neighbors from embedding proximity.

        If project is set, only compute for entries in that project subtree.
        Uses numpy for vectorized cosine similarity when available,
        falls back to pure Python otherwise.

        Returns number of entries with associations computed.
        """
        entries = self._load()
        embedded = [e for e in entries if e.get('embedding')]
        if project is not None:
            embedded = [e for e in embedded
                        if project_matches_filter(e.get('project', ''), project)]

        if len(embedded) < 2:
            return 0

        try:
            import numpy as np
            matrix = np.array([e['embedding'] for e in embedded], dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            normalized = matrix / norms
            similarity = normalized @ normalized.T
            names = [e['name'] for e in embedded]

            for i, entry in enumerate(embedded):
                scores = similarity[i].copy()
                scores[i] = -1
                top_k_idx = np.argsort(scores)[-k:][::-1]
                entry['associations'] = [
                    {'name': names[idx], 'score': round(float(scores[idx]), 4)}
                    for idx in top_k_idx if scores[idx] > -1
                ]
        except ImportError:
            for entry in embedded:
                scores = []
                for other in embedded:
                    if other['name'] == entry['name']:
                        continue
                    score = _cosine_similarity(entry['embedding'], other['embedding'])
                    scores.append({'name': other['name'], 'score': round(score, 4)})
                scores.sort(key=lambda x: x['score'], reverse=True)
                entry['associations'] = scores[:k]

        self._save(entries)
        return sum(1 for e in entries if e.get('associations'))

    @staticmethod
    def _searchable_text(entry):
        """Build searchable text from an entry's text fields."""
        return ' '.join([
            entry.get('name', ''),
            entry.get('description', ''),
            ' '.join(entry.get('observations', [])),
            entry.get('prompt', '') or '',
            entry.get('reasoning', '') or '',
        ]).lower()

    def _score_entry(self, entry, query_embedding=None, mode='semantic',
                     precomputed_relevance=None):
        """Score a memory entry for retrieval ranking.

        Args:
            precomputed_relevance: If provided, use this cosine similarity
                instead of computing it. Used by the numpy batch path.
        """
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

        if precomputed_relevance is not None:
            relevance = precomputed_relevance
        elif query_embedding and entry.get('embedding'):
            relevance = max(0.0, _cosine_similarity(query_embedding, entry['embedding']))
        else:
            relevance = 0.0

        if mode == 'structured':
            w_r, w_i, w_v = 0.3, 0.5, 0.2
        else:
            w_r, w_i, w_v = 0.2, 0.3, 0.5

        has_relevance = (precomputed_relevance is not None
                         or (query_embedding and entry.get('embedding')))
        if not has_relevance:
            w_r += w_v * 0.4
            w_i += w_v * 0.6
            w_v = 0.0

        score = recency * w_r + importance * w_i + relevance * w_v

        backlinks = len(entry.get('backlinks', []))
        if backlinks > 0:
            score += 0.05 * min(backlinks, 5)

        return round(min(score, 1.0), 4)

    def _score_all_entries(self, entries, query, query_embedding):
        """Score all entries against a query. Uses numpy when available."""
        q_lower = query.lower() if query else ''

        if query_embedding:
            try:
                import numpy as np

                embedded_entries = []
                non_embedded = []
                for e in entries:
                    if e.get('embedding'):
                        embedded_entries.append(e)
                    else:
                        non_embedded.append(e)

                results = []

                if embedded_entries:
                    matrix = np.array([e['embedding'] for e in embedded_entries], dtype=np.float32)
                    query_vec = np.array(query_embedding, dtype=np.float32)
                    norms = np.linalg.norm(matrix, axis=1)
                    query_norm = np.linalg.norm(query_vec)
                    similarities = (matrix @ query_vec) / (norms * query_norm + 1e-10)
                    similarities = np.clip(similarities, 0.0, 1.0)

                    for i, entry in enumerate(embedded_entries):
                        score = self._score_entry(
                            entry, precomputed_relevance=float(similarities[i]))
                        if q_lower and q_lower in self._searchable_text(entry):
                            score += 0.1
                        results.append((entry, score))

                for entry in non_embedded:
                    score = self._score_entry(entry, None)
                    if q_lower and q_lower in self._searchable_text(entry):
                        score += 0.1
                    results.append((entry, score))

                return results

            except ImportError:
                pass

        scored = []
        for entry in entries:
            score = self._score_entry(entry, query_embedding)
            if q_lower and q_lower in self._searchable_text(entry):
                score += 0.1
            scored.append((entry, score))
        return scored

    def recall(self, query=None, name=None, depth=2, decay=0.8, limit=10, project=None):
        """Cascade recall with spreading activation.

        Finds seed memories, then expands through relations, backlinks,
        and associations up to depth hops.

        If project is set, scopes traversal to the project hierarchy
        (bidirectional: child sees parent, parent sees child).

        Returns ranked list of dicts with score, hop, channel fields.
        """
        entries = self._load()
        entry_map = {e['name']: e for e in entries if 'name' in e}

        if project is not None:
            entry_map = {k: v for k, v in entry_map.items()
                         if project_matches_scope(v.get('project', ''), project)}
            entries = [e for e in entries if e.get('name') in entry_map]

        if not entry_map:
            return []

        query_embedding = None
        if query:
            try:
                from memoryschema.embeddings import embed_text
                query_embedding = embed_text(query)
            except Exception:
                pass

        seeds = []
        if name and name in entry_map:
            seeds = [entry_map[name]]
        elif query:
            scored = self._score_all_entries(entries, query, query_embedding)
            scored.sort(key=lambda x: x[1], reverse=True)
            seeds = [e for e, _ in scored[:3]]
        else:
            return []

        visited = {}
        queue = []

        for seed in seeds:
            seed_score = self._score_entry(seed, query_embedding)
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
            current_entry, current_score, current_hop = queue.pop(0)
            if current_hop >= depth:
                continue

            next_hop = current_hop + 1
            hop_score = current_score * decay

            for rel in current_entry.get('relations', []):
                target = rel.get('target')
                if target and target in entry_map:
                    neighbor = entry_map[target]
                    neighbor_score = hop_score * self._score_entry(neighbor, query_embedding)
                    result = {
                        'name': target,
                        'score': round(neighbor_score, 4),
                        'hop': next_hop,
                        'channel': 'relation',
                        'relation_type': rel.get('type'),
                        'type': neighbor.get('type'),
                        'importance': neighbor.get('importance'),
                        'description': neighbor.get('description'),
                        'observations': neighbor.get('observations', []),
                    }
                    if target not in visited or result['score'] > visited[target]['score']:
                        visited[target] = result
                        queue.append((neighbor, neighbor_score, next_hop))

            for bl in current_entry.get('backlinks', []):
                source = bl.get('source')
                if source and source in entry_map:
                    neighbor = entry_map[source]
                    neighbor_score = hop_score * self._score_entry(neighbor, query_embedding)
                    result = {
                        'name': source,
                        'score': round(neighbor_score, 4),
                        'hop': next_hop,
                        'channel': 'backlink',
                        'relation_type': bl.get('type'),
                        'type': neighbor.get('type'),
                        'importance': neighbor.get('importance'),
                        'description': neighbor.get('description'),
                        'observations': neighbor.get('observations', []),
                    }
                    if source not in visited or result['score'] > visited[source]['score']:
                        visited[source] = result
                        queue.append((neighbor, neighbor_score, next_hop))

            for assoc in current_entry.get('associations', []):
                assoc_name = assoc.get('name')
                if assoc_name and assoc_name in entry_map:
                    neighbor = entry_map[assoc_name]
                    assoc_score = assoc.get('score', 0.5)
                    neighbor_score = hop_score * assoc_score
                    result = {
                        'name': assoc_name,
                        'score': round(neighbor_score, 4),
                        'hop': next_hop,
                        'channel': 'association',
                        'type': neighbor.get('type'),
                        'importance': neighbor.get('importance'),
                        'description': neighbor.get('description'),
                        'observations': neighbor.get('observations', []),
                    }
                    if assoc_name not in visited or result['score'] > visited[assoc_name]['score']:
                        visited[assoc_name] = result
                        queue.append((neighbor, neighbor_score, next_hop))

        results = sorted(visited.values(), key=lambda x: x['score'], reverse=True)
        return results[:limit]


def _cosine_similarity(a, b):
    """Compute cosine similarity between two vectors. Pure Python."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_store(jsonl_path=None, config=None):
    """Get the best available store backend.

    Tries Neo4j first (L2b). Falls back to JSONL (L1b).
    Graceful degradation — always returns a working store.

    Args:
        jsonl_path: Override JSONL file path.
        config: MemoryConfig instance for defaults.
    """
    try:
        from memoryschema.neo4j_store import Neo4jMemoryStore
        if config:
            store = Neo4jMemoryStore(
                uri=config.neo4j_uri,
                user=config.neo4j_user,
                password=config.neo4j_password,
            )
        else:
            store = Neo4jMemoryStore()
        store.count()
        return store
    except Exception:
        pass

    if jsonl_path is None:
        if config:
            jsonl_path = str(config.store_path)
        else:
            from memoryschema.config import MemoryConfig
            jsonl_path = str(MemoryConfig().store_path)
    return MemoryStore(jsonl_path)
