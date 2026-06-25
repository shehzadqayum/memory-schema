"""Tests for agent inheritance: TOML config and rules resolution."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from memoryschema.inheritance import (
    _walk_upward,
    find_toml_config,
    load_toml_config,
    flatten_toml,
    walk_config_chain,
    merge_config_dicts,
    resolve_config_chain,
    overridden_rules,
    validate_toml_name,
    rules_ancestry,
    resolve_rules,
)


# --- Helpers ---

def _write_toml(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _make_rules(rules_dir, filenames):
    rules_dir.mkdir(parents=True, exist_ok=True)
    for name in filenames:
        (rules_dir / name).write_text(f"# {name} rules")


# --- TOML Parsing ---

class TestFindTomlConfig:
    def test_found(self, tmp_path):
        _write_toml(tmp_path / 'memoryschema.toml', '[project]\nname = "test"')
        assert find_toml_config(tmp_path) == tmp_path / 'memoryschema.toml'

    def test_not_found(self, tmp_path):
        assert find_toml_config(tmp_path) is None


class TestLoadTomlConfig:
    def test_valid(self, tmp_path):
        path = tmp_path / 'memoryschema.toml'
        _write_toml(path, '[project]\nname = "test"\n[neo4j]\nuri = "bolt://custom:7687"')
        result = load_toml_config(path)
        assert result['project']['name'] == 'test'
        assert result['neo4j']['uri'] == 'bolt://custom:7687'

    def test_missing_file(self, tmp_path):
        result = load_toml_config(tmp_path / 'nonexistent.toml')
        assert result == {}

    def test_invalid_syntax(self, tmp_path):
        path = tmp_path / 'memoryschema.toml'
        _write_toml(path, 'this is not valid toml {{{}}}')
        result = load_toml_config(path)
        assert result == {}

    def test_minimal(self, tmp_path):
        path = tmp_path / 'memoryschema.toml'
        _write_toml(path, '[project]\nname = "minimal"')
        result = load_toml_config(path)
        assert result == {'project': {'name': 'minimal'}}

    def test_full(self, tmp_path):
        path = tmp_path / 'memoryschema.toml'
        _write_toml(path, """
[project]
name = "full"

[store]
path = "custom/store.jsonl"

[neo4j]
uri = "bolt://db:7687"
user = "admin"
password = "secret"

[voyage]
embed_model = "voyage-3"

[retrieval]
recency_decay = 0.99
recall_depth = 3
""")
        result = load_toml_config(path)
        assert result['project']['name'] == 'full'
        assert result['neo4j']['uri'] == 'bolt://db:7687'
        assert result['retrieval']['recall_depth'] == 3


class TestFlattenToml:
    def test_nested(self):
        raw = {'neo4j': {'uri': 'bolt://x', 'user': 'admin'}, 'project': {'name': 'test'}}
        flat = flatten_toml(raw)
        assert flat == {'neo4j_uri': 'bolt://x', 'neo4j_user': 'admin', 'project_name': 'test'}

    def test_empty(self):
        assert flatten_toml({}) == {}

    def test_unknown_keys_ignored(self):
        raw = {'unknown_section': {'key': 'value'}, 'neo4j': {'unknown_key': 'val', 'uri': 'bolt://x'}}
        flat = flatten_toml(raw)
        assert flat == {'neo4j_uri': 'bolt://x'}

    def test_partial(self):
        raw = {'retrieval': {'recall_depth': 5}}
        flat = flatten_toml(raw)
        assert flat == {'recall_depth': 5}


# --- Config Chain Walking ---

class TestWalkConfigChain:
    def test_single_project(self, tmp_path):
        _write_toml(tmp_path / 'memoryschema.toml', '[project]\nname = "root"')
        chain = walk_config_chain(tmp_path)
        assert len(chain) == 1
        assert chain[0] == tmp_path / 'memoryschema.toml'

    def test_nested_two_levels(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        child.mkdir(parents=True)
        _write_toml(parent / 'memoryschema.toml', '[project]\nname = "parent"')
        _write_toml(child / 'memoryschema.toml', '[project]\nname = "parent.child"')
        chain = walk_config_chain(child)
        assert len(chain) >= 2
        assert chain[0] == child / 'memoryschema.toml'  # child first
        # Parent should be in chain (use as_posix() so the match is OS-portable)
        assert any(p.as_posix().endswith('parent/memoryschema.toml') for p in chain)

    def test_no_toml(self, tmp_path):
        chain = walk_config_chain(tmp_path)
        assert chain == []

    def test_skips_intermediate_dirs(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        child.mkdir(parents=True)
        _write_toml(parent / 'memoryschema.toml', '[project]\nname = "parent"')
        # No TOML in projects/ (intermediate)
        _write_toml(child / 'memoryschema.toml', '[project]\nname = "child"')
        chain = walk_config_chain(child)
        assert len(chain) == 2  # child + parent, skipped projects/

    def test_deep_nesting_finds_grandparent(self, tmp_path):
        """Fix 1: deep structures (>2 intermediate dirs) still find ancestors."""
        gp = tmp_path / 'grandparent'
        child = gp / 'src' / 'packages' / 'subprojects' / 'child'
        child.mkdir(parents=True)
        _write_toml(gp / 'memoryschema.toml', '[project]\nname = "gp"')
        _write_toml(child / 'memoryschema.toml', '[project]\nname = "child"')
        chain = walk_config_chain(child)
        assert len(chain) == 2
        assert chain[0] == child / 'memoryschema.toml'
        assert chain[1] == gp / 'memoryschema.toml'

    def test_child_only_no_parent(self, tmp_path):
        child = tmp_path / 'projects' / 'child'
        child.mkdir(parents=True)
        _write_toml(child / 'memoryschema.toml', '[project]\nname = "child"')
        chain = walk_config_chain(child)
        assert len(chain) == 1


# --- Config Merging ---

class TestMergeConfigDicts:
    def test_parent_overrides_child(self):
        child = {'neo4j_uri': 'bolt://child:7687', 'project_name': 'child'}
        parent = {'neo4j_uri': 'bolt://parent:7687'}
        merged = merge_config_dicts(child, parent)
        assert merged['neo4j_uri'] == 'bolt://parent:7687'
        assert merged['project_name'] == 'child'

    def test_child_unique_preserved(self):
        child = {'recall_depth': 5}
        parent = {'neo4j_uri': 'bolt://parent:7687'}
        merged = merge_config_dicts(child, parent)
        assert merged['recall_depth'] == 5
        assert merged['neo4j_uri'] == 'bolt://parent:7687'

    def test_parent_unique_applied(self):
        child = {}
        parent = {'neo4j_uri': 'bolt://parent:7687'}
        merged = merge_config_dicts(child, parent)
        assert merged['neo4j_uri'] == 'bolt://parent:7687'

    def test_empty_child(self):
        merged = merge_config_dicts({}, {'a': 1, 'b': 2})
        assert merged == {'a': 1, 'b': 2}

    def test_empty_parent(self):
        merged = merge_config_dicts({'a': 1}, {})
        assert merged == {'a': 1}

    def test_both_empty(self):
        assert merge_config_dicts({}, {}) == {}


# --- Full Resolution ---

class TestResolveConfigChain:
    def test_flat_project(self, tmp_path):
        _write_toml(tmp_path / 'memoryschema.toml',
                     '[project]\nname = "flat"\n[neo4j]\nuri = "bolt://custom:7687"')
        result = resolve_config_chain(tmp_path)
        assert result['project_name'] == 'flat'
        assert result['neo4j_uri'] == 'bolt://custom:7687'

    def test_nested_parent_wins(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        child.mkdir(parents=True)
        _write_toml(parent / 'memoryschema.toml',
                     '[project]\nname = "parent"\n[neo4j]\nuri = "bolt://parent:7687"')
        _write_toml(child / 'memoryschema.toml',
                     '[project]\nname = "parent.child"\n[neo4j]\nuri = "bolt://child:7687"\n[retrieval]\nrecall_depth = 5')
        result = resolve_config_chain(child)
        assert result['neo4j_uri'] == 'bolt://parent:7687'  # parent wins
        assert result['recall_depth'] == 5  # child-unique preserved

    def test_no_toml_fallback(self, tmp_path):
        result = resolve_config_chain(tmp_path)
        assert 'project_root' in result
        assert 'neo4j_uri' not in result  # no TOML, no values

    def test_env_vars_not_in_chain(self, tmp_path):
        """Fix 7: resolve_config_chain does NOT read env vars.
        Env vars are handled by MemoryConfig dataclass defaults."""
        _write_toml(tmp_path / 'memoryschema.toml',
                     '[neo4j]\nuri = "bolt://toml:7687"')
        with patch.dict(os.environ, {'NEO4J_URI': 'bolt://env:7687'}):
            result = resolve_config_chain(tmp_path)
        # TOML value survives — env var override happens at MemoryConfig level
        assert result['neo4j_uri'] == 'bolt://toml:7687'

    def test_cli_overrides_toml(self, tmp_path):
        _write_toml(tmp_path / 'memoryschema.toml',
                     '[project]\nname = "toml-name"')
        from memoryschema.config import MemoryConfig
        config = MemoryConfig.from_toml(tmp_path, cli_overrides={'project_name': 'cli-name'})
        assert config.project_name == 'cli-name'

    def test_from_toml_classmethod(self, tmp_path):
        _write_toml(tmp_path / 'memoryschema.toml',
                     '[project]\nname = "fromtoml"\n[retrieval]\nrecall_depth = 4')
        from memoryschema.config import MemoryConfig
        # Isolate from an ambient MEMORY_PROJECT/MEMORY_ROOT: env overrides TOML by design
        # (see test_from_toml_env_var_beats_toml), so clear them to exercise the TOML path
        # even when run under a configured project (helios .env sets MEMORY_PROJECT).
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('MEMORY_PROJECT', None)
            os.environ.pop('MEMORY_ROOT', None)
            config = MemoryConfig.from_toml(tmp_path)
        assert config.project_name == 'fromtoml'
        assert config.recall_depth == 4

    def test_from_toml_env_var_beats_toml(self, tmp_path):
        """Env vars must override TOML values in from_toml()."""
        _write_toml(tmp_path / 'memoryschema.toml',
                     '[neo4j]\nuri = "bolt://toml:7687"')
        from memoryschema.config import MemoryConfig
        with patch.dict(os.environ, {'NEO4J_URI': 'bolt://env:7687'}):
            config = MemoryConfig.from_toml(tmp_path)
        assert config.neo4j_uri == 'bolt://env:7687'  # env wins

    def test_cli_beats_env_beats_toml(self, tmp_path):
        """Full precedence: CLI > env > TOML (all three set, CLI wins)."""
        _write_toml(tmp_path / 'memoryschema.toml',
                     '[project]\nname = "toml-name"')
        from memoryschema.config import MemoryConfig
        with patch.dict(os.environ, {'MEMORY_PROJECT': 'env-name'}):
            config = MemoryConfig.from_toml(
                tmp_path, cli_overrides={'project_name': 'cli-name'})
        assert config.project_name == 'cli-name'  # CLI wins over env and TOML


# --- Rules Ancestry ---

class TestRulesAncestry:
    def test_single_project(self, tmp_path):
        _make_rules(tmp_path / '.claude' / 'rules', ['memory-schema.md'])
        dirs = rules_ancestry(tmp_path)
        assert len(dirs) == 1

    def test_nested(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['memory-schema.md'])
        _make_rules(child / '.claude' / 'rules', ['custom.md'])
        dirs = rules_ancestry(child)
        assert len(dirs) >= 2
        assert dirs[0] == child / '.claude' / 'rules'  # child first

    def test_no_rules(self, tmp_path):
        dirs = rules_ancestry(tmp_path)
        assert dirs == []

    def test_skips_intermediate_dirs(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['parent.md'])
        # No rules in projects/ (intermediate)
        _make_rules(child / '.claude' / 'rules', ['child.md'])
        dirs = rules_ancestry(child)
        assert len(dirs) == 2  # child + parent, skipped projects/


# --- Rules Resolution ---

class TestResolveRules:
    def test_single_project(self, tmp_path):
        _make_rules(tmp_path / '.claude' / 'rules', ['memory-schema.md', 'memory-working.md'])
        rules, _ = resolve_rules(tmp_path)
        assert len(rules) == 2
        assert all(not r['is_inherited'] for r in rules)

    def test_parent_wins_on_conflict(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['memory-working.md'])
        _make_rules(child / '.claude' / 'rules', ['memory-working.md'])
        rules, _ = resolve_rules(child)
        conflict = [r for r in rules if r['filename'] == 'memory-working.md']
        assert len(conflict) == 1
        assert 'parent' in str(conflict[0]['source_dir'])
        assert conflict[0]['is_inherited'] is True

    def test_child_unique_preserved(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['memory-schema.md'])
        _make_rules(child / '.claude' / 'rules', ['custom.md'])
        rules, _ = resolve_rules(child)
        filenames = [r['filename'] for r in rules]
        assert 'memory-schema.md' in filenames
        assert 'custom.md' in filenames
        custom = [r for r in rules if r['filename'] == 'custom.md'][0]
        assert custom['is_inherited'] is False

    def test_parent_unique_inherited(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['memory-schema.md', 'memory-working.md'])
        _make_rules(child / '.claude' / 'rules', ['custom.md'])
        rules, _ = resolve_rules(child)
        assert len(rules) == 3
        inherited = [r for r in rules if r['is_inherited']]
        assert len(inherited) == 2

    def test_no_rules(self, tmp_path):
        rules, _ = resolve_rules(tmp_path)
        assert rules == []

    def test_child_only_no_parent(self, tmp_path):
        child = tmp_path / 'projects' / 'child'
        _make_rules(child / '.claude' / 'rules', ['memory-schema.md'])
        rules, _ = resolve_rules(child)
        assert len(rules) == 1
        assert rules[0]['is_inherited'] is False

    def test_three_levels_grandparent_wins(self, tmp_path):
        gp = tmp_path / 'gp'
        parent = gp / 'sub' / 'parent'
        child = parent / 'sub' / 'child'
        _make_rules(gp / '.claude' / 'rules', ['shared.md'])
        _make_rules(parent / '.claude' / 'rules', ['shared.md'])
        _make_rules(child / '.claude' / 'rules', ['shared.md'])
        rules, _ = resolve_rules(child)
        shared = [r for r in rules if r['filename'] == 'shared.md']
        assert len(shared) == 1
        assert 'gp' in str(shared[0]['source_dir'])  # grandparent wins

    def test_is_inherited_flag(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['parent-only.md', 'shared.md'])
        _make_rules(child / '.claude' / 'rules', ['child-only.md', 'shared.md'])
        rules, _ = resolve_rules(child)
        by_name = {r['filename']: r for r in rules}
        assert by_name['parent-only.md']['is_inherited'] is True
        assert by_name['shared.md']['is_inherited'] is True  # parent wins
        assert by_name['child-only.md']['is_inherited'] is False

    def test_sorted_by_filename(self, tmp_path):
        _make_rules(tmp_path / '.claude' / 'rules', ['z-rule.md', 'a-rule.md', 'm-rule.md'])
        rules, _ = resolve_rules(tmp_path)
        filenames = [r['filename'] for r in rules]
        assert filenames == sorted(filenames)


# --- Shared walker (Fix 1 & 2) ---

class TestWalkUpward:
    def test_collects_matches(self, tmp_path):
        child = tmp_path / 'a' / 'b'
        child.mkdir(parents=True)
        (tmp_path / 'marker').touch()
        (child / 'marker').touch()
        results = _walk_upward(child, lambda d: d / 'marker' if (d / 'marker').exists() else None)
        assert len(results) >= 2

    def test_skips_non_matches(self, tmp_path):
        child = tmp_path / 'a' / 'b' / 'c'
        child.mkdir(parents=True)
        (tmp_path / 'marker').touch()
        # No marker in a/ or b/
        results = _walk_upward(child, lambda d: d / 'marker' if (d / 'marker').exists() else None)
        assert len(results) == 1

    def test_respects_max_depth(self, tmp_path):
        child = tmp_path / 'a' / 'b' / 'c'
        child.mkdir(parents=True)
        results = _walk_upward(child, lambda d: d, max_depth=2)
        assert len(results) == 2  # child + one parent, not three


# --- Overridden rules (Fix 3) ---

class TestOverriddenRules:
    def test_no_parent(self, tmp_path):
        _make_rules(tmp_path / '.claude' / 'rules', ['a.md'])
        assert overridden_rules(tmp_path) == []

    def test_no_conflict(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['parent.md'])
        _make_rules(child / '.claude' / 'rules', ['child.md'])
        assert overridden_rules(child) == []

    def test_conflict_detected(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['shared.md'])
        _make_rules(child / '.claude' / 'rules', ['shared.md', 'unique.md'])
        overridden = overridden_rules(child)
        assert len(overridden) == 1
        assert overridden[0]['filename'] == 'shared.md'
        assert 'parent' in str(overridden[0]['parent_path'])
        assert 'child' in str(overridden[0]['child_path'])

    def test_multiple_conflicts(self, tmp_path):
        parent = tmp_path / 'parent'
        child = parent / 'projects' / 'child'
        _make_rules(parent / '.claude' / 'rules', ['a.md', 'b.md'])
        _make_rules(child / '.claude' / 'rules', ['a.md', 'b.md', 'c.md'])
        overridden = overridden_rules(child)
        assert len(overridden) == 2
        assert {o['filename'] for o in overridden} == {'a.md', 'b.md'}


# --- TOML name validation (Fix 5) ---

class TestValidateTomlName:
    def test_no_toml(self, tmp_path):
        assert validate_toml_name(tmp_path) is None

    def test_no_name_in_toml(self, tmp_path):
        _write_toml(tmp_path / 'memoryschema.toml', '[retrieval]\nrecall_depth = 3')
        assert validate_toml_name(tmp_path) is None

    def test_matching_name(self, tmp_path):
        # Create a projects/myproject structure so _derive_project works
        child = tmp_path / 'projects' / 'myproject'
        child.mkdir(parents=True)
        _write_toml(child / 'memoryschema.toml', '[project]\nname = "myproject"')
        assert validate_toml_name(child) is None

    def test_mismatched_name(self, tmp_path):
        child = tmp_path / 'projects' / 'myproject'
        child.mkdir(parents=True)
        _write_toml(child / 'memoryschema.toml', '[project]\nname = "wrong-name"')
        warning = validate_toml_name(child)
        assert warning is not None
        assert 'wrong-name' in warning
        assert 'myproject' in warning

    def test_no_derivable_project(self, tmp_path):
        # No projects/ in path, so _derive_project returns None — no warning
        _write_toml(tmp_path / 'memoryschema.toml', '[project]\nname = "anything"')
        assert validate_toml_name(tmp_path) is None
