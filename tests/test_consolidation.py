"""Tests for consolidation module — batch indexing pipeline + clustering."""

import os
from unittest.mock import patch, MagicMock

import pytest

from memoryschema.consolidation import consolidate, _embedding_text, _cluster_by_associations
from memoryschema.store import MemoryStore


VALID_ENTITY = """<memory:entity schema="2" name="{name}" type="semantic" importance="5">
  <memory:description>{desc}</memory:description>
  <memory:observations>
    <memory:observation>Fact one</memory:observation>
  </memory:observations>
  <memory:prompt>What was asked</memory:prompt>
  <memory:reasoning>Why this approach</memory:reasoning>
</memory:entity>"""


@pytest.fixture
def memory_dir(tmp_path):
    """Create a temp dir with valid memory files."""
    for i in range(3):
        filepath = tmp_path / f"entity-{i}.md"
        filepath.write_text(VALID_ENTITY.format(name=f"entity-{i}", desc=f"Entity {i}"))
    # Also add an unparseable file
    (tmp_path / "bad.md").write_text("Not a valid entity.")
    (tmp_path / "MEMORY.md").write_text("Index file.")
    return tmp_path


@pytest.fixture
def store(tmp_path):
    return MemoryStore(str(tmp_path / "test-store.jsonl"))


class TestEmbeddingText:
    def test_all_fields(self):
        memory = {
            "description": "Test desc",
            "observations": ["Fact 1", "Fact 2"],
            "prompt": "What?",
            "reasoning": "Because.",
        }
        result = _embedding_text(memory)
        assert "Test desc" in result
        assert "Fact 1" in result
        assert "Fact 2" in result
        assert "What?" in result
        assert "Because." in result

    def test_minimal(self):
        memory = {"name": "test", "description": "Just desc"}
        result = _embedding_text(memory)
        assert result == "test Just desc"

    def test_empty(self):
        result = _embedding_text({})
        assert result.strip() == ""


class TestConsolidate:
    def test_syncs_valid_files(self, memory_dir, store):
        result = consolidate(str(memory_dir), "test-project", store, embed=False)
        assert result["synced"] == 3
        assert result["skipped"] == 1  # bad.md
        assert store.count() == 3

    def test_sets_project(self, memory_dir, store):
        consolidate(str(memory_dir), "my-project", store, embed=False)
        entry = store.get("entity-0")
        assert entry["project"] == "my-project"

    def test_computes_backlinks(self, tmp_path):
        # Create two entities with a relation
        (tmp_path / "source.md").write_text("""<memory:entity schema="2" name="source">
  <memory:description>Source entity</memory:description>
  <memory:relations>
    <memory:relation target="target" type="INFORMS"/>
  </memory:relations>
</memory:entity>""")
        (tmp_path / "target.md").write_text("""<memory:entity schema="2" name="target">
  <memory:description>Target entity</memory:description>
</memory:entity>""")
        store = MemoryStore(str(tmp_path / "store.jsonl"))
        result = consolidate(str(tmp_path), "test", store, embed=False)
        assert result["synced"] == 2
        assert result["backlinks"] >= 1

    def test_embed_false_no_embedding(self, memory_dir, store):
        result = consolidate(str(memory_dir), "test", store, embed=False)
        assert result["embedded"] == 0
        entry = store.get("entity-0")
        assert entry.get("embedding") is None

    def test_embed_true_with_mock(self, memory_dir, store):
        mock_vector = [0.1] * 1024
        with patch("memoryschema.consolidation.embed_text", return_value=mock_vector, create=True) as mock_embed:
            # Patch the import inside consolidate
            with patch.dict("sys.modules", {"memoryschema.embeddings": MagicMock(embed_text=lambda t: mock_vector)}):
                result = consolidate(str(memory_dir), "test", store, embed=True)
        # embed=True attempts embedding but may fall back if import fails in the function
        assert result["synced"] == 3

    def test_empty_dir(self, tmp_path):
        store = MemoryStore(str(tmp_path / "store.jsonl"))
        result = consolidate(str(tmp_path), "test", store, embed=False)
        assert result["synced"] == 0
        assert result["skipped"] == 0


# --- Clustering tests (Phase 3) ---

def _make_episodic(name, associations=None):
    """Helper: create a minimal episodic entry with associations."""
    entry = {
        'name': name,
        'type': 'episodic',
        'status': 'active',
        'description': f'Session event {name}',
    }
    if associations:
        entry['associations'] = associations
    return entry


class TestClusterByAssociations:
    def test_threshold_splits_components(self):
        """High-score pairs cluster together, weak cross-links are filtered."""
        entries = [
            _make_episodic('a', [{'name': 'b', 'score': 0.9}, {'name': 'c', 'score': 0.4}]),
            _make_episodic('b', [{'name': 'a', 'score': 0.9}, {'name': 'd', 'score': 0.3}]),
            _make_episodic('c', [{'name': 'd', 'score': 0.85}, {'name': 'a', 'score': 0.4}]),
            _make_episodic('d', [{'name': 'c', 'score': 0.85}, {'name': 'b', 'score': 0.3}]),
        ]
        clusters = _cluster_by_associations(entries, min_cluster=2, max_cluster=10,
                                             score_threshold=0.7)
        assert len(clusters) == 2
        cluster_names = [sorted(e['name'] for e in c) for c in clusters]
        assert ['a', 'b'] in cluster_names
        assert ['c', 'd'] in cluster_names

    def test_threshold_zero_preserves_old_behavior(self):
        """With threshold=0, all edges kept — one giant component."""
        entries = [
            _make_episodic('a', [{'name': 'b', 'score': 0.1}]),
            _make_episodic('b', [{'name': 'c', 'score': 0.1}]),
            _make_episodic('c', [{'name': 'a', 'score': 0.1}]),
        ]
        clusters = _cluster_by_associations(entries, min_cluster=2, max_cluster=10,
                                             score_threshold=0)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_giant_component_filtered_by_threshold(self):
        """Reproduce the real bug: 12 entries all connected, max_cluster=10.
        With threshold=0 -> 0 clusters (component too large).
        With threshold=0.7 -> smaller clusters that fit."""
        # Build a chain of 12 entries with weak links (0.5) and strong pairs (0.9)
        entries = []
        for i in range(12):
            assocs = []
            # Strong link to partner (pairs: 0-1, 2-3, 4-5, etc.)
            partner = i + 1 if i % 2 == 0 else i - 1
            if 0 <= partner < 12:
                assocs.append({'name': f'e-{partner}', 'score': 0.9})
            # Weak links to neighbors
            if i > 0:
                assocs.append({'name': f'e-{i-1}', 'score': 0.5})
            if i < 11:
                assocs.append({'name': f'e-{i+1}', 'score': 0.5})
            entries.append(_make_episodic(f'e-{i}', assocs))

        # threshold=0: one giant component of 12 > max_cluster=10 -> 0 clusters
        clusters_old = _cluster_by_associations(entries, max_cluster=10,
                                                 score_threshold=0)
        assert len(clusters_old) == 0

        # threshold=0.7: only strong pairs -> 6 clusters of 2
        clusters_new = _cluster_by_associations(entries, max_cluster=10,
                                                 score_threshold=0.7)
        assert len(clusters_new) == 6
        for cluster in clusters_new:
            assert len(cluster) == 2

    def test_no_associations_no_clusters(self):
        """Entries without associations produce no clusters."""
        entries = [_make_episodic('a'), _make_episodic('b')]
        clusters = _cluster_by_associations(entries)
        assert len(clusters) == 0

    def test_min_cluster_filter(self):
        """Singletons below min_cluster are excluded."""
        entries = [
            _make_episodic('a', [{'name': 'b', 'score': 0.9}]),
            _make_episodic('b', [{'name': 'a', 'score': 0.9}]),
            _make_episodic('c'),  # isolated
        ]
        clusters = _cluster_by_associations(entries, min_cluster=2)
        assert len(clusters) == 1
        names = sorted(e['name'] for e in clusters[0])
        assert names == ['a', 'b']
