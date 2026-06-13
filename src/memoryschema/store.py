"""
JSONL structured store for memory entities (L1b).

Pure Python, zero external dependencies (stdlib only).
One JSON object per line. Atomic writes via temp file + os.replace.
Optional numpy for vectorized scoring (graceful fallback).

v3 features: status filtering (active/superseded/archived/quarantined),
SUPERSEDES trust guards (TRUST_LEVELS provenance hierarchy),
cycle detection (R7), and include_inactive override for queries.

Usage:
    from memoryschema import MemoryStore, get_store
    store = get_store()  # Neo4j if available, JSONL fallback
    store.upsert({'name': 'my-memory', 'type': 'semantic', ...})
    result = store.get('my-memory')
"""

import json
import math
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone

from memoryschema.config import TRUST_LEVELS, VERIFICATION_RANKS
from memoryschema.hierarchy import project_matches_filter, project_matches_scope
from memoryschema.tags import Observation, serialize_observation, deserialize_observation, observation_text


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
        self._audit_path = os.path.join(os.path.dirname(jsonl_path), 'audit.jsonl')
        self._lock_path = jsonl_path + '.lock'

    @contextmanager
    def _file_lock(self):
        """Advisory file lock for read-modify-write atomicity.

        Uses fcntl on Unix. Falls back to no-op on platforms without it.
        Lock is non-blocking — raises IOError on contention.
        """
        lock_dir = os.path.dirname(self._lock_path)
        if lock_dir:
            os.makedirs(lock_dir, exist_ok=True)
        lock_fd = None
        try:
            import fcntl
            lock_fd = open(self._lock_path, 'w')
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except ImportError:
            yield  # No fcntl (Windows) — fall through without lock
        except IOError:
            raise IOError(
                f'JSONL store locked by another process. '
                f'Consider Neo4j for concurrent access.'
            )
        finally:
            if lock_fd is not None:
                try:
                    import fcntl
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except (ImportError, Exception):
                    pass
                lock_fd.close()

    def _audit(self, operation, name, new_dict=None, prior_entry=None):
        """Log a mutation to the audit trail. Non-blocking on failure.

        When both prior_entry and new_dict are given, computes field diffs.
        When only new_dict is given (no prior), passes it directly as changes.
        """
        try:
            from memoryschema.audit import log_mutation, _diff_fields
            if prior_entry and new_dict:
                changes = _diff_fields(prior_entry, new_dict)
            elif new_dict:
                changes = new_dict  # direct changes dict (e.g. criterion capture)
            else:
                changes = None
            log_mutation(self._audit_path, operation, name, changes, prior_entry)
        except Exception:
            pass  # Audit failure must not block mutations

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
                    entry = json.loads(line)
                    self._deserialize_observations(entry)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
        self._cache = entries
        self._cache_mtime = mtime
        return entries

    @staticmethod
    def _serialize_entry(entry):
        """Prepare an entry dict for JSON serialization.

        Observations with basis must be serialized through the
        serialize_observation function — json.dumps on an Observation(str)
        would silently drop basis.
        """
        out = dict(entry)
        if 'observations' in out:
            out['observations'] = [serialize_observation(o) for o in out['observations']]
        return out

    @staticmethod
    def _deserialize_observations(entry):
        """Reconstruct Observation instances from loaded JSONL data.

        Handles both legacy plain strings and v4 {"text","basis"} dicts.
        """
        if 'observations' in entry:
            entry['observations'] = [deserialize_observation(o) for o in entry['observations']]
        return entry

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
                    f.write(json.dumps(self._serialize_entry(entry), ensure_ascii=False) + '\n')
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
        with self._file_lock():
            return self._upsert_inner(memory_dict)

    def _upsert_inner(self, memory_dict):
        entries = self._load()
        name = memory_dict.get('name')
        existing = None
        for entry in entries:
            if entry.get('name') == name:
                existing = entry
                break

        now = _now_iso()

        # Pre-validate SUPERSEDES relations (trust guard + cycle detection R7)
        new_rels = memory_dict.get('relations', [])
        if any(r.get('type') == 'SUPERSEDES' for r in new_rels):
            pre_map = {e['name']: e for e in entries if 'name' in e}
            source_prov = (memory_dict.get('provenance')
                           or (existing.get('provenance', 'first-party')
                               if existing else 'first-party'))
            existing_pairs = set()
            if existing:
                existing_pairs = {(r.get('target'), r.get('type'))
                                  for r in existing.get('relations', [])}
            for rel in new_rels:
                if rel.get('type') != 'SUPERSEDES':
                    continue
                target_name = rel.get('target')
                if not target_name or (target_name, 'SUPERSEDES') in existing_pairs:
                    continue
                if target_name in pre_map:
                    target_prov = pre_map[target_name].get('provenance', 'first-party')
                    source_trust = TRUST_LEVELS.get(source_prov, 1)
                    target_trust = TRUST_LEVELS.get(target_prov, 1)
                    if source_trust < target_trust:
                        raise ValueError(
                            f"Trust guard: {source_prov!r} cannot supersede "
                            f"{target_prov!r} (insufficient authority)")
                    # Verification guard (v4): source rank ≥ target rank
                    source_obs = memory_dict.get('observations', [])
                    if existing:
                        source_obs = source_obs or existing.get('observations', [])
                    source_rank = max(
                        (VERIFICATION_RANKS.get(
                            o.basis if isinstance(o, Observation) else None, 2)
                         for o in source_obs),
                        default=2)
                    target_entry = pre_map[target_name]
                    target_rank = max(
                        (VERIFICATION_RANKS.get(
                            o.basis if isinstance(o, Observation) else None, 2)
                         for o in target_entry.get('observations', [])),
                        default=2)
                    if source_rank < target_rank:
                        raise ValueError(
                            f"Verification guard: source rank {source_rank} cannot "
                            f"supersede target rank {target_rank}")
                    if self._detect_supersedes_cycle(entries, name, target_name):
                        raise ValueError(
                            f"SUPERSEDES cycle detected: {name} → {target_name} "
                            f"would create a circular chain")

        if existing is None:
            new_entry = dict(memory_dict)
            new_entry['created_at'] = now
            new_entry['last_accessed'] = now
            new_entry['access_count'] = 0
            # Set verified_at if any measured observation present
            if any(isinstance(o, Observation) and o.basis == 'measured'
                   for o in new_entry.get('observations', [])):
                new_entry['verified_at'] = now
            entries.append(new_entry)

            # Side effects for new entries with relations
            if new_entry.get('relations'):
                entry_map = {e['name']: e for e in entries if 'name' in e}
                for rel in new_entry.get('relations', []):
                    target_name = rel.get('target')
                    rel_type = rel.get('type')
                    if not target_name or target_name not in entry_map:
                        continue
                    if rel_type == 'SUPERSEDES':
                        target = entry_map[target_name]
                        if target.get('status', 'active') == 'active':
                            target['status'] = 'superseded'
                            self._audit('supersede', target_name, {
                                'criterion': target.get('description', ''),
                                'superseded_by': name,
                            })
                            try:
                                from memoryschema.audit import log_force
                                log_force(self._audit_path, 'supersession',
                                          target_name, source=name)
                            except Exception:
                                pass
                    if rel_type == 'MITIGATES':
                        self._audit('mitigate', target_name, {
                            'mitigated_by': name,
                        })
                    if rel_type == 'CONTRADICTS' and name:
                        target = entry_map[target_name]
                        target_rels = target.get('relations', [])
                        reverse = (name, 'CONTRADICTS')
                        tpairs = {(r.get('target'), r.get('type'))
                                  for r in target_rels}
                        if reverse not in tpairs:
                            target_rels.append({'target': name, 'type': 'CONTRADICTS'})
                            target['relations'] = target_rels
                            try:
                                from memoryschema.audit import log_force
                                log_force(self._audit_path, 'contradiction',
                                          target_name, source=name)
                            except Exception:
                                pass

            self._save(entries)
            self._audit('create', name)
            return new_entry

        # Capture prior state for audit
        prior_snapshot = dict(existing)

        # Merge (schema, filepath, provenance, project are immutable after creation)
        for key in ('type', 'status', 'description', 'importance',
                     'body', 'source', 'prompt', 'reasoning'):
            if key in memory_dict and memory_dict[key] is not None:
                existing[key] = memory_dict[key]

        # Observation merge with basis upgrade (v4)
        existing_obs = existing.get('observations', [])
        new_obs = memory_dict.get('observations', [])
        # Build text→index map for existing observations
        existing_text_map = {}
        for i, o in enumerate(existing_obs):
            existing_text_map.setdefault(observation_text(o), i)
        has_measured = False
        for obs in new_obs:
            text = observation_text(obs)
            obs_basis = obs.basis if isinstance(obs, Observation) else None
            if text in existing_text_map:
                # Duplicate text — check for basis upgrade
                idx = existing_text_map[text]
                stored = existing_obs[idx]
                stored_basis = stored.basis if isinstance(stored, Observation) else None
                new_rank = VERIFICATION_RANKS.get(obs_basis, 2)
                stored_rank = VERIFICATION_RANKS.get(stored_basis, 2)
                if obs_basis is not None and new_rank > stored_rank:
                    # Higher rank → upgrade
                    existing_obs[idx] = Observation(text, basis=obs_basis)
                    self._audit('basis_upgrade', existing.get('name'),
                                {'observation': text, 'from': stored_basis, 'to': obs_basis})
                    if obs_basis == 'measured':
                        has_measured = True
                # Lower/equal → skip (ordinary duplicate)
            else:
                existing_obs.append(obs if isinstance(obs, Observation) else Observation(text, basis=obs_basis))
                existing_text_map[text] = len(existing_obs) - 1
                if obs_basis == 'measured':
                    has_measured = True
        existing['observations'] = existing_obs

        # Advance verified_at if any measured observation was added or upgraded
        if has_measured or any(
            (isinstance(o, Observation) and o.basis == 'measured')
            for o in memory_dict.get('observations', [])
        ):
            existing['verified_at'] = now

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

        # Relation side-effects: SUPERSEDES and CONTRADICTS
        name = memory_dict.get('name') or existing.get('name')
        entry_map = {e['name']: e for e in entries if 'name' in e}
        for rel in existing_rels:
            target_name = rel.get('target')
            rel_type = rel.get('type')
            if not target_name or target_name not in entry_map:
                continue

            # SUPERSEDES → mark target as superseded + capture criterion + force record
            if rel_type == 'SUPERSEDES':
                target = entry_map[target_name]
                if target.get('status', 'active') == 'active':
                    target['status'] = 'superseded'
                    self._audit('supersede', target_name, {
                        'criterion': target.get('description', ''),
                        'superseded_by': name,
                    })
                    # Force record: supersession
                    try:
                        from memoryschema.audit import log_force
                        log_force(self._audit_path, 'supersession',
                                  target_name, source=name)
                    except Exception:
                        pass

            # MITIGATES → audit only, no status change, target stays active
            if rel_type == 'MITIGATES':
                self._audit('mitigate', target_name, {
                    'mitigated_by': name,
                })

            # CONTRADICTS → ensure symmetric edge on target + force record
            if rel_type == 'CONTRADICTS' and name:
                target = entry_map[target_name]
                target_rels = target.get('relations', [])
                reverse_pair = (name, 'CONTRADICTS')
                target_pairs = {(r.get('target'), r.get('type'))
                                for r in target_rels}
                if reverse_pair not in target_pairs:
                    target_rels.append({'target': name, 'type': 'CONTRADICTS'})
                    target['relations'] = target_rels
                    # Force record: contradiction
                    try:
                        from memoryschema.audit import log_force
                        log_force(self._audit_path, 'contradiction',
                                  target_name, source=name)
                    except Exception:
                        pass

        existing['last_accessed'] = now

        self._save(entries)
        self._audit('upsert', name, memory_dict, prior_snapshot)
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

    def search(self, query=None, type=None, project=None, limit=10,
               include_inactive=False):
        """Search memories by query text, type, and/or project.

        Query does case-insensitive substring match across
        name, description, observations, prompt, reasoning, and body.
        Returns list of matching entry dicts (up to limit).
        Excludes non-active entries unless include_inactive=True.
        """
        entries = self._load()
        results = []

        for entry in entries:
            if not include_inactive and entry.get('status', 'active') != 'active':
                continue
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
        """Delete a memory by name. Cleans up inbound relations. Returns True if found."""
        with self._file_lock():
            return self._delete_inner(name)

    def _delete_inner(self, name):
        entries = self._load()
        new_entries = [e for e in entries if e.get('name') != name]
        if len(new_entries) == len(entries):
            return False
        # Remove inbound relations pointing to the deleted entry
        for entry in new_entries:
            rels = entry.get('relations', [])
            entry['relations'] = [r for r in rels if r.get('target') != name]
            bls = entry.get('backlinks', [])
            entry['backlinks'] = [b for b in bls if b.get('source') != name]
        self._save(new_entries)
        self._audit('delete', name)
        return True

    def archive(self, name):
        """Set a memory's status to archived. Returns True if found."""
        with self._file_lock():
            return self._archive_inner(name)

    def _archive_inner(self, name):
        entries = self._load()
        for entry in entries:
            if entry.get('name') == name:
                entry['status'] = 'archived'
                self._save(entries)
                self._audit('archive', name)
                return True
        return False

    @staticmethod
    def _detect_supersedes_cycle(entries, source_name, target_name):
        """Check if adding SUPERSEDES from source to target creates a cycle.

        Follows existing SUPERSEDES chains from target — if source is
        reachable, adding source→target would create a cycle (R7).
        """
        entry_map = {e['name']: e for e in entries if 'name' in e}
        visited = set()
        queue = [target_name]
        while queue:
            current = queue.pop(0)
            if current == source_name:
                return True
            if current in visited:
                continue
            visited.add(current)
            entry = entry_map.get(current)
            if entry:
                for rel in entry.get('relations', []):
                    if rel.get('type') == 'SUPERSEDES':
                        t = rel.get('target')
                        if t and t not in visited:
                            queue.append(t)
        return False

    def unarchive(self, name):
        """Set an archived memory back to active. Returns True if found and was archived."""
        with self._file_lock():
            entries = self._load()
            for entry in entries:
                if entry.get('name') == name:
                    if entry.get('status') != 'archived':
                        return False
                    entry['status'] = 'active'
                    self._save(entries)
                    self._audit('unarchive', name)
                    return True
            return False

    def reactivate(self, name):
        """Set a superseded memory back to active. Returns True if found and was superseded."""
        with self._file_lock():
            entries = self._load()
            for entry in entries:
                if entry.get('name') == name:
                    if entry.get('status') != 'superseded':
                        return False
                    entry['status'] = 'active'
                    self._save(entries)
                    self._audit('reactivate', name)
                    return True
            return False

    def release_quarantine(self, name):
        """Set a quarantined memory back to active. Returns True if found and was quarantined."""
        with self._file_lock():
            entries = self._load()
            for entry in entries:
                if entry.get('name') == name:
                    if entry.get('status') != 'quarantined':
                        return False
                    entry['status'] = 'active'
                    self._save(entries)
                    self._audit('release_quarantine', name)
                    return True
            return False

    def list_all(self, project=None, include_inactive=False):
        """Return all entries, optionally filtered to a project subtree.

        Excludes non-active entries by default unless include_inactive=True.
        """
        entries = self._load()
        if not include_inactive:
            entries = [e for e in entries
                       if e.get('status', 'active') == 'active']
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

    @staticmethod
    def _bm25_score(query, document, k1=1.2, b=0.75, avg_dl=50):
        """Pure-Python BM25 score for a single query-document pair.

        Tokenizes on whitespace. Returns a score in [0, ~0.3] range
        suitable as a boost added to the base retrieval score.
        """
        if not query or not document:
            return 0.0
        query_terms = query.lower().split()
        doc_terms = document.lower().split()
        dl = len(doc_terms)
        if dl == 0:
            return 0.0

        # Term frequencies in document
        tf = {}
        for term in doc_terms:
            tf[term] = tf.get(term, 0) + 1

        score = 0.0
        for qt in query_terms:
            f = tf.get(qt, 0)
            if f == 0:
                continue
            # BM25 term score (without IDF — single document context)
            numerator = f * (k1 + 1)
            denominator = f + k1 * (1 - b + b * dl / avg_dl)
            score += numerator / denominator

        # Normalize to a boost range (~0.0 to 0.3)
        return min(score * 0.1, 0.3)

    @staticmethod
    def _multi_space_relevance(entry, query_embedding):
        """Compute combined relevance across all available embedding spaces.

        Uses per-space cosine similarities combined through the space combiner.
        Falls back to single embedding for legacy entries without embeddings dict.
        """
        from memoryschema.spaces import combine_similarities as _combine_sims

        per_space_sims = {}
        embeddings = entry.get('embeddings', {})

        if embeddings:
            for space_name, space_vec in embeddings.items():
                if space_vec:
                    per_space_sims[space_name] = max(
                        0.0, _cosine_similarity(query_embedding, space_vec))
        elif entry.get('embedding'):
            per_space_sims['default'] = max(
                0.0, _cosine_similarity(query_embedding, entry['embedding']))

        if not per_space_sims:
            return 0.0
        return _combine_sims(per_space_sims)

    def _score_entry(self, entry, query_embedding=None, mode='semantic',
                     precomputed_relevance=None):
        """Score a memory entry for retrieval ranking.

        Args:
            precomputed_relevance: If provided, use this combined relevance
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

        # Type-dependent recency modifier
        entry_type = entry.get('type', 'semantic')
        if entry_type == 'semantic':
            recency = max(recency, 0.6)  # floor at 0.6 — persistent knowledge
        elif entry_type == 'procedural':
            # Access reinforcement: frequently accessed procedures decay slower
            # exponent = 1/(1 + 0.3*min(access_count, 10))
            # At 0 accesses: exponent=1.0 (standard decay)
            # At 10 accesses: exponent=0.25 (very slow decay)
            access_count = min(entry.get('access_count') or 0, 10)
            exponent = 1.0 / (1.0 + 0.3 * access_count)
            recency = recency ** exponent
        # episodic: standard decay (no modification)

        importance = entry.get('importance', 5)
        if importance is None:
            importance = 5
        importance = importance / 10.0

        if precomputed_relevance is not None:
            relevance = precomputed_relevance
        elif query_embedding:
            relevance = self._multi_space_relevance(entry, query_embedding)
        else:
            relevance = 0.0

        if mode == 'structured':
            w_r, w_i, w_v = 0.3, 0.5, 0.2
        else:
            w_r, w_i, w_v = 0.2, 0.3, 0.5

        has_relevance = (precomputed_relevance is not None
                         or (query_embedding and (
                             entry.get('embeddings') or entry.get('embedding'))))
        if not has_relevance:
            w_r += w_v * 0.4
            w_i += w_v * 0.6
            w_v = 0.0

        score = recency * w_r + importance * w_i + relevance * w_v

        # Hub bonus: log-scale to prevent rich-get-richer compounding
        backlinks = len(entry.get('backlinks', []))
        if backlinks > 0:
            score += 0.05 * math.log(1 + backlinks)

        # Trust multiplier: ingested content ranks lower by default
        provenance = entry.get('provenance', 'first-party')
        trust_multipliers = {
            'first-party': 1.0,
            'user': 1.0,
            'derived': 0.9,
            'ingested': 0.7,
        }
        score *= trust_multipliers.get(provenance, 0.8)

        # Basis factor (v4): lowest-reliability labelled observation biases ranking
        basis_multipliers = {'measured': 1.0, 'inferred': 0.97, 'reported': 0.93}
        labelled_bases = [
            o.basis for o in entry.get('observations', [])
            if isinstance(o, Observation) and o.basis is not None
        ]
        if labelled_bases:
            worst = min(labelled_bases, key=lambda b: VERIFICATION_RANKS.get(b, 2))
            score *= basis_multipliers.get(worst, 1.0)
        # No labelled observations → neutral (1.0), no effect

        # MITIGATES dampening: entries with inbound MITIGATES score slightly lower
        mitigates_count = sum(
            1 for bl in entry.get('backlinks', [])
            if bl.get('type') == 'MITIGATES'
        )
        if mitigates_count > 0:
            score *= 0.95  # mitigation_dampening default

        return round(min(score, 1.0), 4)

    def _score_all_entries(self, entries, query, query_embedding):
        """Score all entries against a query. Uses numpy when available.

        Multi-space aware: computes per-space cosine similarities in batch
        via numpy, combines through the space combiner, then scores.
        Falls back to per-entry scoring without numpy.
        """
        q_lower = query.lower() if query else ''

        if query_embedding:
            try:
                import numpy as np
                from memoryschema.spaces import combine_similarities as _combine_sims

                query_vec = np.array(query_embedding, dtype=np.float32)
                query_norm = np.linalg.norm(query_vec)

                # Collect per-entry space embeddings (multi-space or legacy)
                entry_space_embs = []  # list of (entry, {space: vec})
                non_embedded = []
                for e in entries:
                    space_embs = e.get('embeddings', {})
                    if not space_embs and e.get('embedding'):
                        space_embs = {'default': e['embedding']}
                    if space_embs:
                        entry_space_embs.append((e, space_embs))
                    else:
                        non_embedded.append(e)

                results = []

                if entry_space_embs:
                    # Discover all spaces present across entries
                    all_spaces = set()
                    for _, se in entry_space_embs:
                        all_spaces.update(se.keys())

                    # Batch compute cosine similarity per space
                    space_sims = {}  # space -> {entry_idx: sim}
                    for space_name in all_spaces:
                        indices = []
                        vecs = []
                        for idx, (_, se) in enumerate(entry_space_embs):
                            if space_name in se and se[space_name]:
                                indices.append(idx)
                                vecs.append(se[space_name])
                        if vecs:
                            matrix = np.array(vecs, dtype=np.float32)
                            norms = np.linalg.norm(matrix, axis=1)
                            sims = (matrix @ query_vec) / (norms * query_norm + 1e-10)
                            sims = np.clip(sims, 0.0, 1.0)
                            space_sims[space_name] = {
                                indices[i]: float(sims[i])
                                for i in range(len(indices))
                            }

                    # Combine per-space similarities for each entry
                    for idx, (entry, _) in enumerate(entry_space_embs):
                        per_space = {}
                        for space_name, idx_sim_map in space_sims.items():
                            if idx in idx_sim_map:
                                per_space[space_name] = idx_sim_map[idx]
                        combined = _combine_sims(per_space) if per_space else 0.0
                        score = self._score_entry(
                            entry, precomputed_relevance=combined)
                        if q_lower:
                            score += self._bm25_score(
                                q_lower, self._searchable_text(entry))
                        results.append((entry, score))

                for entry in non_embedded:
                    score = self._score_entry(entry, None)
                    if q_lower:
                        score += self._bm25_score(q_lower, self._searchable_text(entry))
                    results.append((entry, score))

                return results

            except ImportError:
                pass

        scored = []
        for entry in entries:
            score = self._score_entry(entry, query_embedding)
            if q_lower:
                score += self._bm25_score(q_lower, self._searchable_text(entry))
            scored.append((entry, score))
        return scored

    def recall(self, query=None, name=None, depth=2, decay=0.8, limit=10,
               project=None, include_inactive=False, max_inherit_depth=3):
        """Cascade recall with spreading activation.

        Finds seed memories, then expands through relations, backlinks,
        and associations up to depth hops.

        If project is set, scopes traversal to the project hierarchy
        (bidirectional: child sees parent, parent sees child).
        Excludes non-active entries unless include_inactive=True.

        Returns ranked list of dicts with score, hop, channel fields.
        """
        entries = self._load()
        entry_map = {e['name']: e for e in entries if 'name' in e}

        if project is not None:
            entry_map = {k: v for k, v in entry_map.items()
                         if project_matches_scope(
                             v.get('project', ''), project,
                             max_depth=max_inherit_depth)}

        if not entry_map:
            return []

        # Returnable set: active entries only (unless include_inactive).
        # Non-active entries stay in entry_map for BFS traversal
        # (traversable-not-returned: superseded entries bridge graph walks).
        if not include_inactive:
            returnable = {k for k, v in entry_map.items()
                          if v.get('status', 'active') == 'active'}
        else:
            returnable = set(entry_map.keys())

        scorable_entries = [entry_map[n] for n in returnable]

        query_embedding = None
        if query:
            try:
                from memoryschema.embeddings import embed_text
                query_embedding = embed_text(query)
            except Exception:
                pass

        seeds = []
        if name and name in entry_map and name in returnable:
            seeds = [entry_map[name]]
        elif query:
            scored = self._score_all_entries(scorable_entries, query, query_embedding)
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

        # Filter to returnable entries (traversable-not-returned)
        results = sorted(
            [r for r in visited.values() if r['name'] in returnable],
            key=lambda x: x['score'], reverse=True)

        # Rerank stage: use Voyage reranker if available and query provided
        if query and len(results) > limit:
            try:
                from memoryschema.embeddings import rerank as _rerank
                rerank_candidates = results[:limit * 3]
                documents = [
                    f"{r['name']}: {r.get('description', '')}"
                    for r in rerank_candidates
                ]
                reranked = _rerank(query, documents, limit=limit)
                reranked_indices = {rr['index'] for rr in reranked}
                results = [rerank_candidates[rr['index']] for rr in reranked]
            except Exception:
                pass  # Rerank unavailable — fall back to cascade scoring

        # Add provenance and untrusted marker to each result
        for r in results:
            entry = entry_map.get(r['name'])
            if entry:
                prov = entry.get('provenance', 'first-party')
                r['provenance'] = prov
                r['untrusted'] = prov == 'ingested'
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
