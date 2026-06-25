"""Project hierarchy utilities for dot-notation nesting.

Encodes agent hierarchy as dot-separated project names:
  'parent.child.grandchild'

Two matching modes:
  - scope: bidirectional (recall — child sees parent, parent sees child)
  - filter: subtree-only (search/list — parent sees children, not vice versa)
"""

import re

_KEBAB_SEGMENT = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def parse_project_path(project):
    """Split dot-notation project into segments.

    'a.b.c' -> ['a', 'b', 'c']
    'single' -> ['single']
    None or '' -> []
    """
    if not project:
        return []
    return project.split('.')


def project_depth(project):
    """Return nesting depth. 'a' -> 0, 'a.b' -> 1, 'a.b.c' -> 2."""
    segments = parse_project_path(project)
    return max(len(segments) - 1, 0)


def parent_project(project):
    """Return parent project name, or None if root.

    'a.b.c' -> 'a.b'
    'a' -> None
    """
    segments = parse_project_path(project)
    if len(segments) <= 1:
        return None
    return '.'.join(segments[:-1])


def ancestor_projects(project):
    """Return all ancestor project names, nearest first.

    'a.b.c' -> ['a.b', 'a']
    'a' -> []
    """
    segments = parse_project_path(project)
    ancestors = []
    for i in range(len(segments) - 1, 0, -1):
        ancestors.append('.'.join(segments[:i]))
    return ancestors


def is_ancestor_of(candidate, project):
    """True if candidate is a strict ancestor of project.

    is_ancestor_of('a', 'a.b.c') -> True
    is_ancestor_of('a.b', 'a.b.c') -> True
    is_ancestor_of('a.b.c', 'a.b.c') -> False (not strict)
    is_ancestor_of('a', 'a') -> False
    is_ancestor_of('x', 'a.b') -> False
    """
    if not candidate or not project or candidate == project:
        return False
    return project.startswith(candidate + '.')


def is_descendant_of(candidate, project):
    """True if candidate is a strict descendant of project.

    is_descendant_of('a.b.c', 'a') -> True
    is_descendant_of('a.b', 'a') -> True
    is_descendant_of('a', 'a') -> False (not strict)
    is_descendant_of('a', 'a.b') -> False
    """
    if not candidate or not project or candidate == project:
        return False
    return candidate.startswith(project + '.')


def project_matches_scope(entry_project, scope_project, max_depth=None):
    """True if entry is within scope (bidirectional).

    Used for recall — child sees parent memories (inheritance),
    parent sees child memories (read-down).

    Matches: exact, ancestor, or descendant.

    Args:
        max_depth: Maximum hierarchy levels of separation allowed.
            None = unlimited (default, backward compatible).
            1 = only direct parent/child.
            2 = up to grandparent/grandchild.

    project_matches_scope('a.b', 'a') -> True   (descendant)
    project_matches_scope('a', 'a.b') -> True   (ancestor, inheritance)
    project_matches_scope('a.b', 'a.b') -> True (exact)
    project_matches_scope('x', 'a') -> False    (unrelated)
    project_matches_scope(None, 'a') -> True   (unscoped = universal)
    project_matches_scope('a', None) -> False
    """
    if not scope_project:
        return False
    if not entry_project:
        return True  # unscoped entities are universally visible
    if entry_project == scope_project:
        return True

    is_related = (entry_project.startswith(scope_project + '.') or
                  scope_project.startswith(entry_project + '.'))
    if not is_related:
        return False

    if max_depth is None:
        return True

    # Count separation: difference in depth between the two projects
    entry_depth = entry_project.count('.')
    scope_depth = scope_project.count('.')
    separation = abs(entry_depth - scope_depth)
    return separation <= max_depth


def project_matches_filter(entry_project, filter_project):
    """True if entry is the project itself or a descendant (subtree-only).

    Used for search/list — parent sees children, children do NOT see parent.

    project_matches_filter('a.b', 'a') -> True   (descendant)
    project_matches_filter('a', 'a.b') -> False  (parent, not included)
    project_matches_filter('a.b', 'a.b') -> True (exact)
    project_matches_filter('x', 'a') -> False    (unrelated)
    project_matches_filter(None, 'a') -> True   (unscoped = universal)
    project_matches_filter('a', None) -> False
    """
    if not filter_project:
        return False
    if not entry_project:
        return True  # unscoped entities are universally visible
    if entry_project == filter_project:
        return True
    return entry_project.startswith(filter_project + '.')


def validate_project_name(project):
    """Validate dot-notation project name. Returns list of error strings.

    Rules: each segment must be kebab-case, no empty segments,
    no leading/trailing dots.
    """
    errors = []
    if not project:
        errors.append('Project name is empty')
        return errors
    if project.startswith('.'):
        errors.append('Leading dot')
    if project.endswith('.'):
        errors.append('Trailing dot')
    if '..' in project:
        errors.append('Empty segment (consecutive dots)')
    for segment in project.split('.'):
        if not segment:
            continue  # already caught by above checks
        if not _KEBAB_SEGMENT.match(segment):
            errors.append(f'Segment {segment!r} is not kebab-case')
    return errors
