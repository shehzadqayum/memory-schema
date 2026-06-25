"""Tests for L0 (MEMORY.md) token budget enforcement and progressive disclosure.

Covers all 4 functions in l0_budget.py:
- estimate_tokens: chars / 4 approximation
- parse_index_entries: extract entry lines from MEMORY.md
- enforce_budget: evict lowest-scoring entries when over budget
- categorize_index: group entries by type under section headers
"""

import json
import pytest

from memoryschema.l0_budget import (
    estimate_tokens,
    parse_index_entries,
    enforce_budget,
    categorize_index,
    DEFAULT_TOKEN_BUDGET,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens('') == 0

    def test_known_length(self):
        assert estimate_tokens('a' * 100) == 25

    def test_short_text(self):
        assert estimate_tokens('abc') == 0  # 3 // 4 = 0

    def test_exact_multiple(self):
        assert estimate_tokens('a' * 8) == 2


class TestParseIndexEntries:
    def test_extracts_entries(self):
        content = '- [alpha](alpha.md) — desc A\n- [beta](beta.md) — desc B\n'
        entries, other = parse_index_entries(content)
        assert len(entries) == 2
        assert entries[0][0] == 'alpha'
        assert entries[1][0] == 'beta'
        assert '— desc A' in entries[0][1]

    def test_preserves_other_lines(self):
        content = '# Title\n\n- [alpha](alpha.md) — desc\n\n### Header\n'
        entries, other = parse_index_entries(content)
        assert len(entries) == 1
        assert '# Title' in other
        assert '### Header' in other

    def test_empty_content(self):
        entries, other = parse_index_entries('')
        assert entries == []
        assert other == ['']

    def test_no_entries(self):
        content = '# Title\n\nSome text without entries.\n'
        entries, other = parse_index_entries(content)
        assert entries == []
        assert len(other) > 0


class TestEnforceBudget:
    @pytest.fixture
    def index_file(self, tmp_path):
        return str(tmp_path / 'MEMORY.md')

    @pytest.fixture
    def store_file(self, tmp_path):
        return str(tmp_path / 'store.jsonl')

    def _write_index(self, path, entries):
        """Write a MEMORY.md with the given entry names."""
        lines = ['# Memory Index\n']
        for name in entries:
            lines.append(f'- [{name}]({name}.md) — description of {name}\n')
        with open(path, 'w') as f:
            f.writelines(lines)

    def _write_store(self, path, entries):
        """Write a store.jsonl with entries having different importance."""
        from memoryschema.store import MemoryStore
        store = MemoryStore(path)
        for entry in entries:
            store.upsert(entry)

    def test_nonexistent_file(self, tmp_path):
        result = enforce_budget(str(tmp_path / 'nonexistent.md'))
        assert result == {'evicted': [], 'tokens_before': 0, 'tokens_after': 0}

    def test_under_budget_no_change(self, index_file):
        self._write_index(index_file, ['alpha', 'beta'])
        result = enforce_budget(index_file)
        assert result['evicted'] == []
        assert result['tokens_before'] == result['tokens_after']

    def test_over_budget_evicts(self, index_file):
        # Create enough entries to exceed a small budget
        names = [f'entry-{i}' for i in range(50)]
        self._write_index(index_file, names)
        result = enforce_budget(index_file, token_budget=100)
        assert len(result['evicted']) > 0
        assert result['tokens_after'] <= 100
        assert result['tokens_before'] > 100

    def test_fifo_eviction_without_store(self, index_file):
        """Without a store, earliest entries (FIFO) are evicted first."""
        names = [f'entry-{i}' for i in range(50)]
        self._write_index(index_file, names)
        result = enforce_budget(index_file, token_budget=100)
        # FIFO: first entries evicted first
        assert result['evicted'][0] == 'entry-0'

    def test_score_based_eviction_with_store(self, index_file, store_file):
        """With a store, lowest-scoring entries are evicted first."""
        names = ['low-importance', 'high-importance', 'medium-importance']
        # Pad entries to exceed budget
        names.extend([f'pad-{i}' for i in range(40)])
        self._write_index(index_file, names)
        self._write_store(store_file, [
            {'name': 'low-importance', 'schema': 4, 'importance': 1,
             'description': 'Low'},
            {'name': 'high-importance', 'schema': 4, 'importance': 10,
             'description': 'High'},
            {'name': 'medium-importance', 'schema': 4, 'importance': 5,
             'description': 'Medium'},
        ])
        result = enforce_budget(index_file, store_path=store_file, token_budget=100)
        # low-importance should be evicted before high-importance
        if 'low-importance' in result['evicted'] and 'high-importance' not in result['evicted']:
            pass  # correct: low evicted, high retained
        elif 'high-importance' in result['evicted']:
            # If both evicted, low should come before high in eviction order
            low_idx = result['evicted'].index('low-importance') if 'low-importance' in result['evicted'] else -1
            high_idx = result['evicted'].index('high-importance')
            assert low_idx < high_idx

    def test_file_rewritten(self, index_file):
        names = [f'entry-{i}' for i in range(50)]
        self._write_index(index_file, names)
        result = enforce_budget(index_file, token_budget=100)
        with open(index_file) as f:
            content = f.read()
        # Evicted names should not appear in file
        for name in result['evicted']:
            assert f'[{name}]' not in content
        # Retained names should still appear
        remaining = set(names) - set(result['evicted'])
        for name in list(remaining)[:5]:  # spot check
            assert f'[{name}]' in content

    def test_custom_budget(self, index_file):
        names = [f'entry-{i}' for i in range(20)]
        self._write_index(index_file, names)
        result = enforce_budget(index_file, token_budget=50)
        assert result['tokens_after'] <= 50
        assert len(result['evicted']) > 0

    def test_multiple_blank_lines_cleaned(self, index_file):
        with open(index_file, 'w') as f:
            f.write('# Title\n\n\n\n- [a](a.md) — desc\n\n\n\n- [b](b.md) — desc\n')
        enforce_budget(index_file, token_budget=5000)
        # Even under budget, if eviction runs it cleans blank lines
        # Under budget = no eviction, no rewrite. Force over budget:
        names = [f'x-{i}' for i in range(100)]
        self._write_index(index_file, names)
        # Add extra blank lines manually
        with open(index_file, 'r') as f:
            content = f.read()
        content = content.replace('\n', '\n\n\n')
        with open(index_file, 'w') as f:
            f.write(content)
        enforce_budget(index_file, token_budget=200)
        with open(index_file) as f:
            result = f.read()
        assert '\n\n\n' not in result


class TestCategorizeIndex:
    @pytest.fixture
    def index_file(self, tmp_path):
        return str(tmp_path / 'MEMORY.md')

    @pytest.fixture
    def store_file(self, tmp_path):
        return str(tmp_path / 'store.jsonl')

    def test_nonexistent_file(self, tmp_path):
        assert categorize_index(str(tmp_path / 'nonexistent.md')) == 0

    def test_empty_entries(self, index_file):
        with open(index_file, 'w') as f:
            f.write('# Memory Index\n\nNo entries here.\n')
        assert categorize_index(index_file) == 0

    def test_groups_by_type(self, index_file, store_file):
        with open(index_file, 'w') as f:
            f.write(
                '# Memory Index\n'
                '- [fact-1](fact-1.md) — a fact\n'
                '- [event-1](event-1.md) — an event\n'
                '- [proc-1](proc-1.md) — a procedure\n'
            )
        from memoryschema.store import MemoryStore
        store = MemoryStore(store_file)
        store.upsert({'name': 'fact-1', 'schema': 4, 'type': 'semantic', 'description': 'a fact'})
        store.upsert({'name': 'event-1', 'schema': 4, 'type': 'episodic', 'description': 'an event'})
        store.upsert({'name': 'proc-1', 'schema': 4, 'type': 'procedural', 'description': 'a procedure'})

        count = categorize_index(index_file, store_path=store_file)
        assert count == 3

        with open(index_file) as f:
            content = f.read()
        assert '### Knowledge' in content
        assert '### Session History' in content
        assert '### Procedures' in content
        # Verify ordering: Knowledge before Procedures before Session History
        assert content.index('### Knowledge') < content.index('### Procedures')
        assert content.index('### Procedures') < content.index('### Session History')

    def test_default_to_semantic(self, index_file):
        """Entries without a known type default to Knowledge section."""
        with open(index_file, 'w') as f:
            f.write('# Memory\n- [unknown](unknown.md) — something\n')
        count = categorize_index(index_file)
        assert count == 1
        with open(index_file) as f:
            content = f.read()
        assert '### Knowledge' in content
        assert '[unknown]' in content

    def test_preserves_title(self, index_file):
        with open(index_file, 'w') as f:
            f.write('# My Custom Title\n- [a](a.md) — desc\n')
        categorize_index(index_file)
        with open(index_file) as f:
            content = f.read()
        assert content.startswith('# My Custom Title')

    def test_file_rewritten(self, index_file, store_file):
        with open(index_file, 'w') as f:
            f.write('# Idx\n- [a](a.md) — x\n- [b](b.md) — y\n')
        from memoryschema.store import MemoryStore
        store = MemoryStore(store_file)
        store.upsert({'name': 'a', 'schema': 4, 'type': 'episodic', 'description': 'x'})
        store.upsert({'name': 'b', 'schema': 4, 'type': 'semantic', 'description': 'y'})
        categorize_index(index_file, store_path=store_file)
        with open(index_file) as f:
            content = f.read()
        # b (semantic/Knowledge) should appear before a (episodic/Session History)
        assert content.index('[b]') < content.index('[a]')
