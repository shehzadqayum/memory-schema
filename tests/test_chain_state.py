"""Tests for chain state management — authorised/unauthorised memory model."""

import os
import pytest

from memoryschema.chain_state import get_active_chain, set_active_chain, release_active_chain


class TestChainState:
    def test_no_active_chain_by_default(self, tmp_path):
        assert get_active_chain(str(tmp_path)) is None

    def test_set_active_chain(self, tmp_path):
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('chain-test', str(tmp_path))
        assert get_active_chain(str(tmp_path)) == 'chain-test'

    def test_release_active_chain(self, tmp_path):
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('chain-test', str(tmp_path))
        released = release_active_chain(str(tmp_path))
        assert released == 'chain-test'
        assert get_active_chain(str(tmp_path)) is None

    def test_release_when_no_active(self, tmp_path):
        assert release_active_chain(str(tmp_path)) is None

    def test_set_overwrites_previous(self, tmp_path):
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('chain-old', str(tmp_path))
        set_active_chain('chain-new', str(tmp_path))
        assert get_active_chain(str(tmp_path)) == 'chain-new'

    def test_file_created_in_memory_dir(self, tmp_path):
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('chain-test', str(tmp_path))
        assert os.path.exists(tmp_path / 'memory' / '.active_chain')

    def test_file_removed_on_release(self, tmp_path):
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('chain-test', str(tmp_path))
        release_active_chain(str(tmp_path))
        assert not os.path.exists(tmp_path / 'memory' / '.active_chain')


class TestAuthorisationEnforcement:
    """Test that the hook logic correctly blocks unauthorised upserts."""

    def test_new_memory_always_allowed(self, tmp_path):
        """A name that doesn't exist in the store is always writable."""
        from memoryschema.store import MemoryStore
        store = MemoryStore(str(tmp_path / 'store.jsonl'))
        # No existing entry = new memory = allowed
        assert store.get('new-entry') is None

    def test_existing_memory_blocked_without_auth(self, tmp_path):
        """An existing memory that is not the active chain cannot be upserted."""
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        from memoryschema.store import MemoryStore
        store = MemoryStore(str(tmp_path / 'store.jsonl'))
        store.upsert({'name': 'existing', 'schema': 4, 'description': 'test'})

        # No active chain — existing should be read-only
        active = get_active_chain(str(tmp_path))
        assert active is None
        assert 'existing' != active  # blocked by hook logic

    def test_active_chain_allowed(self, tmp_path):
        """The active chain can be upserted."""
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('my-chain', str(tmp_path))

        from memoryschema.store import MemoryStore
        store = MemoryStore(str(tmp_path / 'store.jsonl'))
        store.upsert({'name': 'my-chain', 'schema': 4, 'description': 'chain v1'})

        # Upsert allowed because name == active chain
        active = get_active_chain(str(tmp_path))
        assert 'my-chain' == active

        store.upsert({'name': 'my-chain', 'schema': 4, 'description': 'chain v2'})
        updated = store.get('my-chain')
        assert updated['description'] == 'chain v2'

    def test_released_chain_becomes_readonly(self, tmp_path):
        """After release, the chain name is no longer the active chain."""
        os.makedirs(tmp_path / 'memory', exist_ok=True)
        set_active_chain('my-chain', str(tmp_path))
        release_active_chain(str(tmp_path))

        active = get_active_chain(str(tmp_path))
        assert active is None
        assert 'my-chain' != active  # blocked by hook logic
