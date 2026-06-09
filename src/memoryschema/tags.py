"""
Memory tag parser.

Parses <memory:entity> tagged files into structured dicts.
Pure Python, zero external dependencies (stdlib xml.etree only).

Reuses XML parsing primitives from validator.py (DRY).
"""

import xml.etree.ElementTree as ET

from memoryschema.validator import extract_entity_block, parse_entity


def _derive_project(filepath):
    """Extract project name from filepath.

    Looks for 'projects/<name>/' segments in the path.
    Supports nested projects: projects/parent/projects/child/ -> parent.child

    Returns the project name (dot-notation) or None.
    Segments that are empty or not kebab-case are skipped.
    """
    if not filepath:
        return None
    import re
    _kebab = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
    normalized = filepath.replace('\\', '/')
    parts = normalized.split('/')
    segments = []
    i = 0
    while i < len(parts):
        if parts[i] == 'projects' and i + 1 < len(parts):
            seg = parts[i + 1]
            if seg and _kebab.match(seg):
                segments.append(seg)
            i += 2
        else:
            i += 1
    if segments:
        return '.'.join(segments)
    return None


def parse_memory_content(content, filepath=None):
    """Parse memory file content into a structured dict.

    Args:
        content: Raw file content as string.
        filepath: Optional filepath for project derivation.

    Returns:
        Dict with all schema fields, or None if content cannot be parsed.
    """
    entity_xml, body = extract_entity_block(content)
    if entity_xml is None:
        return None

    try:
        root = parse_entity(entity_xml)
    except ET.ParseError:
        return None

    name = root.get('name')
    if not name:
        return None

    # Schema version (default 1 if missing)
    schema_str = root.get('schema')
    schema = 1
    if schema_str is not None:
        try:
            schema = int(schema_str)
        except ValueError:
            schema = 1

    # Type (defaults to 'semantic' per schema when omitted)
    type_val = root.get('type') or 'semantic'

    # Status (v3, defaults to 'active' when omitted)
    status = root.get('status') or 'active'

    # Importance
    importance = None
    importance_str = root.get('importance')
    if importance_str is not None:
        try:
            importance = int(importance_str)
        except ValueError:
            pass

    # Description
    desc_elem = root.find('description')
    description = desc_elem.text if desc_elem is not None and desc_elem.text else ''

    # Observations
    observations = []
    obs_elem = root.find('observations')
    if obs_elem is not None:
        for obs in obs_elem.findall('observation'):
            if obs.text:
                observations.append(obs.text)

    # Prompt (v2)
    prompt_elem = root.find('prompt')
    prompt = prompt_elem.text if prompt_elem is not None and prompt_elem.text else None

    # Reasoning (v2)
    reasoning_elem = root.find('reasoning')
    reasoning = reasoning_elem.text if reasoning_elem is not None and reasoning_elem.text else None

    # Relations
    relations = []
    rels_elem = root.find('relations')
    if rels_elem is not None:
        for rel in rels_elem.findall('relation'):
            target = rel.get('target')
            rel_type = rel.get('type')
            if target or rel_type:
                relations.append({'target': target, 'type': rel_type})

    # Source
    source_elem = root.find('source')
    source = source_elem.text if source_elem is not None and source_elem.text else None

    # Project: check entity child first, then derive from filepath
    project_elem = root.find('project')
    if project_elem is not None and project_elem.text:
        project = project_elem.text
    else:
        project = _derive_project(filepath)

    # Backward compat: 'related' list derived from relation targets
    related = [r['target'] for r in relations if r.get('target')]

    return {
        'name': name,
        'schema': schema,
        'type': type_val,
        'status': status,
        'importance': importance,
        'description': description,
        'observations': observations,
        'prompt': prompt,
        'reasoning': reasoning,
        'relations': relations,
        'body': body,
        'source': source,
        'project': project,
        'filepath': filepath,
        'related': related,
    }


def parse_memory_file(filepath):
    """Parse a memory file at the given path.

    Args:
        filepath: Path to a .md memory file.

    Returns:
        Dict with all schema fields, or None if the file cannot be
        read or parsed.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (OSError, IOError):
        return None

    return parse_memory_content(content, filepath=str(filepath))
