"""Regression tests for the supersession/status fixes (2026-06-24).

Bugs fixed:
- parse_memory_file no longer defaults status to 'active' for a status-less .md, so a re-index (or any
  re-upsert) does not revert a server-managed superseded/archived store status.
- A status-less entity is still treated as ACTIVE by list_all (guards the dict.get('status','active')
  pitfall: omitting the key — not setting it to None — keeps the default working).
- migration.entry_to_node_props carries 'status' so a jsonl->neo4j rebuild preserves it.
"""
from memoryschema.tags import parse_memory_file
from memoryschema.store import MemoryStore
from memoryschema.migration import entry_to_node_props

STATUSLESS_MD = (
    '<memory:entity schema="4" name="no-status" type="semantic">\n'
    '  <memory:description>An entity whose .md declares no status</memory:description>\n'
    '  <memory:observations><memory:observation>a fact</memory:observation></memory:observations>\n'
    '</memory:entity>\n'
)


def test_parse_omits_status_when_absent(tmp_path):
    p = tmp_path / "no-status.md"
    p.write_text(STATUSLESS_MD, encoding="utf-8")
    parsed = parse_memory_file(str(p))
    # status must be omitted (or None) so an upsert won't override the store's server-managed status
    assert parsed.get('status') is None


def test_statusless_entity_treated_as_active(tmp_path):
    s = MemoryStore(str(tmp_path / "store.jsonl"))
    s.upsert({'name': 'no-status', 'schema': 4, 'type': 'semantic', 'description': 'd'})  # no status key
    assert 'no-status' in [e['name'] for e in s.list_all()]  # default excludes inactive


def test_reindex_does_not_revert_supersession(tmp_path):
    s = MemoryStore(str(tmp_path / "store.jsonl"))
    s.upsert({'name': 'no-status', 'schema': 4, 'type': 'semantic', 'description': 'orig'})
    s.upsert({'name': 'sup', 'schema': 4, 'type': 'semantic', 'description': 's',
              'relations': [{'target': 'no-status', 'type': 'SUPERSEDES'}]})
    assert s.get('no-status')['status'] == 'superseded'
    # re-index path: parse the status-less .md and upsert it
    p = tmp_path / "no-status.md"
    p.write_text(STATUSLESS_MD, encoding="utf-8")
    s.upsert(parse_memory_file(str(p)))
    assert s.get('no-status')['status'] == 'superseded'  # must NOT revert to active


def test_migration_entry_to_node_props_carries_status():
    props = entry_to_node_props({'name': 'x', 'schema': 4, 'type': 'semantic',
                                 'status': 'superseded', 'description': 'd'})
    assert props['status'] == 'superseded'
