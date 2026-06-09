"""Agent inheritance: TOML config loading and rules resolution.

Implements parent-absolute authority:
  - Parent's rules override child's on filename conflict
  - Parent's config values override child's on key conflict
  - Child self-governs when parent is absent

Uses marker-based upward walk — intermediate directories without
markers are skipped, walk continues to filesystem root (up to max_depth).
"""

import os
import tomllib
from pathlib import Path


# TOML section.key → MemoryConfig field name
_TOML_FIELD_MAP = {
    'project.name': 'project_name',
    'store.path': 'store_path',
    'neo4j.uri': 'neo4j_uri',
    'neo4j.user': 'neo4j_user',
    'neo4j.password': 'neo4j_password',
    'neo4j.container_name': 'neo4j_container_name',
    'neo4j.http_port': 'neo4j_http_port',
    'neo4j.bolt_port': 'neo4j_bolt_port',
    'voyage.api_key': 'voyage_api_key',
    'voyage.embed_model': 'embed_model',
    'voyage.embed_dimensions': 'embed_dimensions',
    'voyage.rerank_model': 'rerank_model',
    'retrieval.recency_decay': 'recency_decay',
    'retrieval.association_k': 'association_k',
    'retrieval.recall_depth': 'recall_depth',
    'retrieval.recall_decay': 'recall_decay',
}

# Environment variable → MemoryConfig field name
_ENV_FIELD_MAP = {
    'NEO4J_URI': 'neo4j_uri',
    'NEO4J_USER': 'neo4j_user',
    'NEO4J_PASSWORD': 'neo4j_password',
    'VOYAGE_API_KEY': 'voyage_api_key',
    'MEMORY_PROJECT': 'project_name',
}

TOML_FILENAME = 'memoryschema.toml'


# --- Shared walker (Fixes 1 & 2) ---

def _walk_upward(start, predicate, max_depth=20):
    """Walk upward from start, collecting results where predicate matches.

    Args:
        start: Starting directory.
        predicate: Callable(Path) → value or None. Non-None values are collected.
        max_depth: Maximum parent directories to traverse. Default 20.

    Returns results in child-first order. Skips intermediate directories
    where predicate returns None. Stops at filesystem root or max_depth.
    """
    results = []
    current = Path(start).resolve()

    for _ in range(max_depth):
        value = predicate(current)
        if value is not None:
            results.append(value)

        parent = current.parent
        if parent == current:
            break  # filesystem root
        current = parent

    return results


# --- TOML loading ---

def find_toml_config(project_root):
    """Find memoryschema.toml in the given directory.

    Returns the Path or None if not found.
    """
    path = Path(project_root) / TOML_FILENAME
    if path.is_file():
        return path
    return None


def load_toml_config(path):
    """Parse a single TOML file. Returns dict or empty dict on error."""
    try:
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def flatten_toml(toml_dict):
    """Convert nested TOML sections to flat MemoryConfig field names.

    {'neo4j': {'uri': 'bolt://...'}} → {'neo4j_uri': 'bolt://...'}
    Unknown keys are silently ignored.
    """
    flat = {}
    for section_key, field_name in _TOML_FIELD_MAP.items():
        section, key = section_key.split('.', 1)
        if section in toml_dict and key in toml_dict[section]:
            flat[field_name] = toml_dict[section][key]
    return flat


# --- Config chain ---

def walk_config_chain(project_root):
    """Walk upward from project_root collecting memoryschema.toml paths.

    Returns child-first order. Skips intermediate directories.
    """
    return _walk_upward(project_root, find_toml_config)


def merge_config_dicts(child, parent):
    """Merge two flat config dicts. Parent wins on conflict.

    For any key present in both, parent's value is used.
    Child-only keys are preserved.
    """
    merged = dict(child)
    merged.update(parent)  # parent overwrites child
    return merged


def resolve_config_chain(project_root, cli_overrides=None):
    """Full config resolution with inheritance chain.

    Resolution order (highest to lowest precedence):
    1. Environment variables
    2. cli_overrides dict
    3. Parent TOML (wins over child on conflict)
    4. Child TOML
    5. (MemoryConfig defaults applied at construction time)

    Returns a dict suitable for MemoryConfig(**result).
    """
    chain = walk_config_chain(project_root)

    # Start with empty, merge child-first then parent overrides
    merged = {}
    for toml_path in chain:
        raw = load_toml_config(toml_path)
        flat = flatten_toml(raw)
        merged = merge_config_dicts(merged, flat)

    # CLI overrides beat TOML (higher precedence)
    if cli_overrides:
        effective = {k: v for k, v in cli_overrides.items() if v is not None}
        merged = merge_config_dicts(merged, effective)

    # Environment variables beat everything
    env_overrides = {}
    for env_var, field_name in _ENV_FIELD_MAP.items():
        val = os.environ.get(env_var)
        if val is not None:
            env_overrides[field_name] = val
    if env_overrides:
        merged = merge_config_dicts(merged, env_overrides)

    # Ensure project_root is set
    merged.setdefault('project_root', str(project_root))

    # Advisory: validate TOML project name matches directory structure (Fix 5)
    name_warning = validate_toml_name(project_root)
    if name_warning:
        merged.setdefault('_name_warning', name_warning)

    return merged


# --- Rules ---

def _rules_dir_predicate(directory):
    """Predicate for _walk_upward: returns rules dir Path or None."""
    rules_dir = directory / '.claude' / 'rules'
    if rules_dir.is_dir():
        return rules_dir
    return None


def rules_ancestry(project_root):
    """Walk upward collecting .claude/rules/ directories.

    Returns child-first order. Skips intermediate directories.
    """
    return _walk_upward(project_root, _rules_dir_predicate)


def resolve_rules(project_root):
    """Resolve effective rules with parent-wins inheritance.

    Returns list of dicts:
        {'filename': str, 'source_dir': Path, 'full_path': Path, 'is_inherited': bool}

    Parent wins on filename conflict. Child's unique rules are additive.
    """
    dirs = rules_ancestry(project_root)
    if not dirs:
        return []

    child_dir = dirs[0]

    # Start with child's rules
    rules_map = {}
    for path in sorted(child_dir.glob('*.md')):
        rules_map[path.name] = {
            'filename': path.name,
            'source_dir': child_dir,
            'full_path': path,
            'is_inherited': False,
        }

    # Parent dirs override — process root-ancestor first so highest wins
    for rules_dir in reversed(dirs[1:]):
        for path in sorted(rules_dir.glob('*.md')):
            filename = path.name
            rules_map[filename] = {
                'filename': filename,
                'source_dir': rules_dir,
                'full_path': path,
                'is_inherited': True,
            }

    return sorted(rules_map.values(), key=lambda r: r['filename'])


def overridden_rules(project_root):
    """Return child rules that are shadowed by a parent (Fix 3).

    Returns list of dicts:
        {'filename': str, 'child_path': Path, 'parent_path': Path}
    """
    dirs = rules_ancestry(project_root)
    if len(dirs) < 2:
        return []

    child_dir = dirs[0]
    child_files = {p.name: p for p in child_dir.glob('*.md')}

    parent_files = {}
    for rules_dir in reversed(dirs[1:]):
        for path in rules_dir.glob('*.md'):
            parent_files[path.name] = path  # root-ancestor wins

    overridden = []
    for filename, child_path in sorted(child_files.items()):
        if filename in parent_files:
            overridden.append({
                'filename': filename,
                'child_path': child_path,
                'parent_path': parent_files[filename],
            })

    return overridden


# --- TOML name validation (Fix 5) ---

def validate_toml_name(project_root):
    """Check if project.name in TOML matches the directory structure.

    Returns a warning string if mismatched, or None if valid/no TOML.
    Advisory only — does not prevent operation.
    """
    from memoryschema.tags import _derive_project

    toml_path = find_toml_config(project_root)
    if toml_path is None:
        return None

    raw = load_toml_config(toml_path)
    toml_name = raw.get('project', {}).get('name')
    if not toml_name:
        return None

    derived = _derive_project(str(project_root))
    if derived and derived != toml_name:
        return (f"TOML project.name '{toml_name}' does not match "
                f"directory-derived name '{derived}'")
    return None
