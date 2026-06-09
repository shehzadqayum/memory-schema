"""Agent inheritance: TOML config loading and rules resolution.

Implements parent-absolute authority:
  - Parent's rules override child's on filename conflict
  - Parent's config values override child's on key conflict
  - Child self-governs when parent is absent

Walk stops at a gap (no memoryschema.toml or .claude/rules/).
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


def walk_config_chain(project_root):
    """Walk upward from project_root collecting memoryschema.toml paths.

    Returns child-first order. Skips intermediate directories (e.g.
    projects/) that don't have a TOML file. Stops after 2 consecutive
    non-TOML directories above the starting point (no managed agents above).
    """
    chain = []
    current = Path(project_root).resolve()
    misses = 0

    while True:
        toml_path = find_toml_config(current)
        if toml_path is not None:
            chain.append(toml_path)
            misses = 0
        else:
            if current != Path(project_root).resolve():
                misses += 1
                if misses > 2:
                    break

        parent = current.parent
        if parent == current:
            break  # filesystem root
        current = parent

    return chain


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
        # Each parent in the chain overrides what came before
        merged = merge_config_dicts(merged, flat)

    # CLI overrides beat TOML (higher precedence)
    if cli_overrides:
        # Filter out None values from CLI defaults
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

    return merged


def rules_ancestry(project_root):
    """Walk upward collecting .claude/rules/ directories.

    Returns child-first order. Skips intermediate directories (e.g.
    projects/) that don't have rules. Stops after 2 consecutive
    non-rules directories above the starting point.
    """
    dirs = []
    current = Path(project_root).resolve()
    misses = 0

    while True:
        rules_dir = current / '.claude' / 'rules'
        if rules_dir.is_dir():
            dirs.append(rules_dir)
            misses = 0
        else:
            if current != Path(project_root).resolve():
                misses += 1
                if misses > 2:
                    break

        parent = current.parent
        if parent == current:
            break  # filesystem root
        current = parent

    return dirs


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

    # Collect child's own filenames first
    child_filenames = set()
    if child_dir.is_dir():
        child_filenames = {p.name for p in child_dir.glob('*.md')}

    # Start with child's rules
    rules_map = {}
    for path in sorted(child_dir.glob('*.md')):
        rules_map[path.name] = {
            'filename': path.name,
            'source_dir': child_dir,
            'full_path': path,
            'is_inherited': False,
        }

    # Walk parent dirs (dirs[1:] are parents, nearest first, but we want
    # root-ancestor to win, so process in reverse = root first)
    for rules_dir in reversed(dirs[1:]):
        for path in sorted(rules_dir.glob('*.md')):
            filename = path.name
            # Parent always overwrites — whether child had it or not
            rules_map[filename] = {
                'filename': filename,
                'source_dir': rules_dir,
                'full_path': path,
                'is_inherited': True,
            }

    return sorted(rules_map.values(), key=lambda r: r['filename'])
