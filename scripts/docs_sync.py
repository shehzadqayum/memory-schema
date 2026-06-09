#!/usr/bin/env python3
"""Synchronize documentation constants with the live codebase.

Extracts test count, doctor check count, test file count, and
Python version requirement from the codebase and verifies they
match all documentation files. Run with --fix to update docs.

Usage:
    python scripts/docs_sync.py          # check only (exit 1 on drift)
    python scripts/docs_sync.py --fix    # update docs in place
"""

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files to check/update (relative to project root)
DOC_FILES = [
    'docs/schema.md',
    'docs/system-overview.md',
    'docs/technical-reference.md',
    'docs/implementation-guide.md',
    'docs/hierarchy-and-inheritance.md',
    'README.md',
]


def get_test_count():
    """Run pytest --co -q and count collected tests."""
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/', '--co'],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    # Look for "N tests collected" or "N test collected"
    for line in result.stdout.strip().split('\n'):
        m = re.search(r'(\d+) tests? collected', line)
        if m:
            return int(m.group(1))
    return None


def get_test_file_count():
    """Count test_*.py files."""
    return len(list((PROJECT_ROOT / 'tests').glob('test_*.py')))


def get_doctor_check_count():
    """Count _check() calls in doctor_cmd.py."""
    doctor = PROJECT_ROOT / 'src' / 'memoryschema' / 'cli' / 'doctor_cmd.py'
    content = doctor.read_text()
    return len(re.findall(r'checks\.append\(_check\(', content))


def get_python_version():
    """Read requires-python from pyproject.toml."""
    pyproject = PROJECT_ROOT / 'pyproject.toml'
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject.read_text())
    return m.group(1) if m else None


def get_relation_type_count():
    """Count relation types from config.py."""
    config = PROJECT_ROOT / 'src' / 'memoryschema' / 'config.py'
    content = config.read_text()
    m = re.search(r'VALID_RELATION_TYPES\s*=\s*frozenset\(\{([^}]+)\}', content)
    if m:
        return len(re.findall(r"'[A-Z_]+'", m.group(1)))
    return None


def check_file(filepath, constants, fix=False):
    """Check a file for stale constants. Returns list of issues."""
    path = PROJECT_ROOT / filepath
    if not path.exists():
        return []

    content = path.read_text()
    issues = []
    new_content = content

    test_count = constants['test_count']
    test_files = constants['test_file_count']
    doctor_checks = constants['doctor_checks']
    python_ver = constants['python_version']
    rel_types = constants['relation_types']

    # Check test counts (e.g., "390 tests", "24 files", "24 test files")
    for m in re.finditer(r'(\d+)\s+tests?\b', content):
        n = int(m.group(1))
        if n != test_count and n > 100:  # ignore small numbers
            issues.append(f'{filepath}: "{m.group(0)}" should be "{test_count} tests"')
            if fix:
                new_content = new_content.replace(m.group(0), f'{test_count} tests')

    for m in re.finditer(r'(\d+)\s+test files?\b', content):
        n = int(m.group(1))
        if n != test_files:
            issues.append(f'{filepath}: "{m.group(0)}" should be "{test_files} test files"')
            if fix:
                new_content = new_content.replace(m.group(0), f'{test_files} test files')

    # Check doctor check counts (e.g., "20 checks", "20 live checks")
    for m in re.finditer(r'(\d+)\s+(live\s+)?checks\b', content):
        n = int(m.group(1))
        if n != doctor_checks and n >= 15:  # ignore small numbers
            issues.append(f'{filepath}: "{m.group(0)}" should be "{doctor_checks} checks"')

    # Check Python version (e.g., "Python 3.11+", "Python >= 3.11")
    for m in re.finditer(r'Python\s+(?:>=?\s*)?(\d+\.\d+)\+?', content):
        ver = m.group(1)
        expected = python_ver.lstrip('>=')
        if ver != expected:
            issues.append(f'{filepath}: Python version "{ver}" should be "{expected}"')

    if fix and new_content != content:
        path.write_text(new_content)

    return issues


def main():
    fix = '--fix' in sys.argv

    # Extract constants
    test_count = get_test_count()
    test_files = get_test_file_count()
    doctor_checks = get_doctor_check_count()
    python_ver = get_python_version()
    rel_types = get_relation_type_count()

    constants = {
        'test_count': test_count,
        'test_file_count': test_files,
        'doctor_checks': doctor_checks,
        'python_version': python_ver,
        'relation_types': rel_types,
    }

    print(f'Live constants:')
    print(f'  Tests: {test_count} across {test_files} files')
    print(f'  Doctor checks: {doctor_checks}')
    print(f'  Python: {python_ver}')
    print(f'  Relation types: {rel_types}')
    print()

    all_issues = []
    for filepath in DOC_FILES:
        issues = check_file(filepath, constants, fix=fix)
        all_issues.extend(issues)

    if all_issues:
        for issue in all_issues:
            print(f'  DRIFT: {issue}')
        if fix:
            print(f'\nFixed {len(all_issues)} issue(s).')
        else:
            print(f'\n{len(all_issues)} issue(s) found. Run with --fix to update.')
        return 1
    else:
        print('All docs in sync.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
