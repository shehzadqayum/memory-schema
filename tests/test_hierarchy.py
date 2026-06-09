"""Tests for project hierarchy utilities."""

import pytest

from memoryschema.hierarchy import (
    parse_project_path,
    project_depth,
    parent_project,
    ancestor_projects,
    is_ancestor_of,
    is_descendant_of,
    project_matches_scope,
    project_matches_filter,
    validate_project_name,
)


class TestParseProjectPath:
    def test_dotted(self):
        assert parse_project_path('a.b.c') == ['a', 'b', 'c']

    def test_single(self):
        assert parse_project_path('single') == ['single']

    def test_two_levels(self):
        assert parse_project_path('parent.child') == ['parent', 'child']

    def test_none(self):
        assert parse_project_path(None) == []

    def test_empty(self):
        assert parse_project_path('') == []


class TestProjectDepth:
    def test_root(self):
        assert project_depth('a') == 0

    def test_one_level(self):
        assert project_depth('a.b') == 1

    def test_two_levels(self):
        assert project_depth('a.b.c') == 2

    def test_empty(self):
        assert project_depth('') == 0

    def test_none(self):
        assert project_depth(None) == 0


class TestParentProject:
    def test_three_levels(self):
        assert parent_project('a.b.c') == 'a.b'

    def test_two_levels(self):
        assert parent_project('a.b') == 'a'

    def test_root(self):
        assert parent_project('a') is None

    def test_empty(self):
        assert parent_project('') is None

    def test_none(self):
        assert parent_project(None) is None


class TestAncestorProjects:
    def test_three_levels(self):
        assert ancestor_projects('a.b.c') == ['a.b', 'a']

    def test_two_levels(self):
        assert ancestor_projects('a.b') == ['a']

    def test_root(self):
        assert ancestor_projects('a') == []

    def test_empty(self):
        assert ancestor_projects('') == []


class TestIsAncestorOf:
    def test_grandparent(self):
        assert is_ancestor_of('a', 'a.b.c') is True

    def test_parent(self):
        assert is_ancestor_of('a.b', 'a.b.c') is True

    def test_self(self):
        assert is_ancestor_of('a.b.c', 'a.b.c') is False

    def test_unrelated(self):
        assert is_ancestor_of('x', 'a.b') is False

    def test_child(self):
        assert is_ancestor_of('a.b.c', 'a') is False

    def test_empty(self):
        assert is_ancestor_of('', 'a') is False

    def test_none(self):
        assert is_ancestor_of(None, 'a') is False

    def test_prefix_collision(self):
        # 'ab' is NOT an ancestor of 'abc' — must match at dot boundary
        assert is_ancestor_of('ab', 'abc') is False


class TestIsDescendantOf:
    def test_grandchild(self):
        assert is_descendant_of('a.b.c', 'a') is True

    def test_child(self):
        assert is_descendant_of('a.b', 'a') is True

    def test_self(self):
        assert is_descendant_of('a', 'a') is False

    def test_parent(self):
        assert is_descendant_of('a', 'a.b') is False

    def test_unrelated(self):
        assert is_descendant_of('x.y', 'a') is False

    def test_prefix_collision(self):
        assert is_descendant_of('abc', 'ab') is False


class TestProjectMatchesScope:
    def test_exact(self):
        assert project_matches_scope('a.b', 'a.b') is True

    def test_descendant(self):
        assert project_matches_scope('a.b.c', 'a') is True

    def test_ancestor_inheritance(self):
        assert project_matches_scope('a', 'a.b') is True

    def test_unrelated(self):
        assert project_matches_scope('x', 'a') is False

    def test_none_entry_universal(self):
        # Fix 9: unscoped entities are universally visible
        assert project_matches_scope(None, 'a') is True
        assert project_matches_scope('', 'a') is True

    def test_none_scope(self):
        assert project_matches_scope('a', None) is False

    def test_sibling(self):
        assert project_matches_scope('a.x', 'a.y') is False

    def test_deep_descendant(self):
        assert project_matches_scope('a.b.c.d', 'a') is True

    def test_deep_ancestor(self):
        assert project_matches_scope('a', 'a.b.c.d') is True

    # Fix 4: max_depth parameter
    def test_max_depth_none_unlimited(self):
        assert project_matches_scope('a.b.c.d', 'a', max_depth=None) is True

    def test_max_depth_1_direct_only(self):
        assert project_matches_scope('a.b', 'a', max_depth=1) is True
        assert project_matches_scope('a.b.c', 'a', max_depth=1) is False

    def test_max_depth_2(self):
        assert project_matches_scope('a.b.c', 'a', max_depth=2) is True
        assert project_matches_scope('a.b.c.d', 'a', max_depth=2) is False

    def test_max_depth_bidirectional(self):
        # read-up also respects max_depth
        assert project_matches_scope('a', 'a.b', max_depth=1) is True
        assert project_matches_scope('a', 'a.b.c', max_depth=1) is False

    def test_max_depth_exact_match_always(self):
        assert project_matches_scope('a.b', 'a.b', max_depth=0) is True


class TestProjectMatchesFilter:
    def test_exact(self):
        assert project_matches_filter('a.b', 'a.b') is True

    def test_descendant(self):
        assert project_matches_filter('a.b.c', 'a') is True

    def test_parent_excluded(self):
        assert project_matches_filter('a', 'a.b') is False

    def test_unrelated(self):
        assert project_matches_filter('x', 'a') is False

    def test_none_entry_universal(self):
        # Fix 9: unscoped entities are universally visible
        assert project_matches_filter(None, 'a') is True
        assert project_matches_filter('', 'a') is True

    def test_none_filter(self):
        assert project_matches_filter('a', None) is False

    def test_sibling(self):
        assert project_matches_filter('a.x', 'a.y') is False

    def test_prefix_collision(self):
        assert project_matches_filter('abc', 'ab') is False


class TestValidateProjectName:
    def test_valid_simple(self):
        assert validate_project_name('my-project') == []

    def test_valid_dotted(self):
        assert validate_project_name('parent.child') == []

    def test_valid_deep(self):
        assert validate_project_name('a.b.c') == []

    def test_empty(self):
        errors = validate_project_name('')
        assert len(errors) > 0

    def test_none(self):
        errors = validate_project_name(None)
        assert len(errors) > 0

    def test_leading_dot(self):
        errors = validate_project_name('.a')
        assert any('Leading dot' in e for e in errors)

    def test_trailing_dot(self):
        errors = validate_project_name('a.')
        assert any('Trailing dot' in e for e in errors)

    def test_consecutive_dots(self):
        errors = validate_project_name('a..b')
        assert any('Empty segment' in e for e in errors)

    def test_not_kebab(self):
        errors = validate_project_name('Bad Name')
        assert any('not kebab-case' in e for e in errors)

    def test_uppercase(self):
        errors = validate_project_name('Parent.Child')
        assert any('not kebab-case' in e for e in errors)

    def test_mixed_valid_invalid(self):
        errors = validate_project_name('good.BAD')
        assert len(errors) == 1
        assert 'BAD' in errors[0]
