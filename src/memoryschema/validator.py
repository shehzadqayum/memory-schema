"""
Memory schema validator.

Validates <memory:> tagged files against the schema specification.

Validation rules:
  V1-V10: Structure (entity element, attributes, children)
  R1-R5:  Relations (attributes, types, self-reference, duplicates)
  F1, F3: Filesystem (filename match, safe characters)
  Q1-Q7:  Content quality (strict mode only)
"""

import os
import re
import xml.etree.ElementTree as ET


from memoryschema.config import VALID_TYPES, VALID_RELATION_TYPES, SCHEMA_VERSION

KEBAB_CASE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def extract_entity_block(content):
    """Extract <memory:entity>...</memory:entity> block and body text.

    Returns (entity_xml, body_text). Both are None if no entity block found.
    Body is None if no text follows the closing tag.
    """
    match = re.search(
        r'(<memory:entity\b.*?</memory:entity>)', content, re.DOTALL,
    )
    if not match:
        return None, None
    entity_xml = match.group(1)
    body = content[match.end():].strip()
    return entity_xml, body if body else None


def strip_namespace(xml_str):
    """Strip memory: namespace prefix for XML parsing."""
    return xml_str.replace('<memory:', '<').replace('</memory:', '</')


def parse_entity(xml_str):
    """Parse entity XML string into ElementTree element.

    Strips memory: prefix to produce valid XML for stdlib parser.
    Raises xml.etree.ElementTree.ParseError on malformed XML.
    """
    return ET.fromstring(strip_namespace(xml_str))


def validate(content, filepath=None, strict=False):
    """Validate memory file content against schema rules.

    Args:
        content: File content as string.
        filepath: Optional filepath for filesystem rules (F1, F3).
        strict: If True, include content quality checks (Q1, Q2, Q6, Q7).

    Returns:
        List of (rule_id, message) tuples for each validation failure.
        Empty list means the file is valid.
    """
    errors = []

    # V1: exactly one <memory:entity> root element
    entity_count = len(re.findall(r'<memory:entity\s+\w+=', content))
    if entity_count == 0:
        errors.append(('V1', 'No <memory:entity> element found'))
        return errors
    if entity_count > 1:
        errors.append(('V1', f'Found {entity_count} <memory:entity> elements, expected 1'))

    entity_xml, _body = extract_entity_block(content)

    if entity_xml is None:
        errors.append(('V9', 'Unclosed <memory:entity> element'))
        return errors

    # V9: all open tags have matching close tags
    try:
        root = parse_entity(entity_xml)
    except ET.ParseError as e:
        errors.append(('V9', f'XML parse error: {e}'))
        return errors

    # V2: required attributes
    name = root.get('name')
    if not name:
        errors.append(('V2', 'Missing name attribute on <memory:entity>'))

    # V10: schema version
    schema_str = root.get('schema')
    if schema_str is not None:
        try:
            schema_ver = int(schema_str)
            if schema_ver < 1 or schema_ver > SCHEMA_VERSION:
                errors.append(('V10', f'Schema version {schema_ver} out of range, must be 1-{SCHEMA_VERSION}'))
        except ValueError:
            errors.append(('V10', f'Schema "{schema_str}" is not a valid integer'))

    # V3: name matches filename
    if filepath and name:
        expected = f'{name}.md'
        actual = os.path.basename(filepath)
        if actual != expected:
            errors.append(('V3', f'Filename "{actual}" does not match name "{name}" (expected "{expected}")'))

    # V4: type is valid (optional field)
    type_val = root.get('type')
    if type_val and type_val not in VALID_TYPES:
        errors.append(('V4', f'Invalid type "{type_val}", must be one of: {", ".join(sorted(VALID_TYPES))}'))

    # V5: importance is integer 1-10 (optional field)
    importance_str = root.get('importance')
    if importance_str is not None:
        try:
            importance = int(importance_str)
            if importance < 1 or importance > 10:
                errors.append(('V5', f'Importance {importance} out of range, must be 1-10'))
        except ValueError:
            errors.append(('V5', f'Importance "{importance_str}" is not a valid integer'))

    # V6: exactly one <memory:description>
    descriptions = root.findall('description')
    if len(descriptions) == 0:
        errors.append(('V6', 'Missing <memory:description> element'))
    elif len(descriptions) > 1:
        errors.append(('V6', f'Found {len(descriptions)} <memory:description> elements, expected 1'))

    # V7: if observations present, must have at least one observation
    observations_elems = root.findall('observations')
    if observations_elems:
        obs = observations_elems[0].findall('observation')
        if len(obs) == 0:
            errors.append(('V7', 'No <memory:observation> elements inside <memory:observations>'))

    # Content quality (strict mode)
    if strict:
        if name and not KEBAB_CASE.match(name):
            errors.append(('Q1', f'Name "{name}" is not kebab-case'))

        if descriptions:
            desc_text = descriptions[0].text or ''
            if '\n' in desc_text:
                errors.append(('Q2', 'Description contains newlines'))
            if len(desc_text) > 120:
                errors.append(('Q2', f'Description is {len(desc_text)} chars, max 120'))

        if observations_elems:
            obs = observations_elems[0].findall('observation')
            if len(obs) > 10:
                errors.append(('Q6', f'{len(obs)} observations, recommended max 10'))
            for i, o in enumerate(obs, 1):
                text = o.text or ''
                word_count = len(text.split())
                if word_count > 50:
                    errors.append(('Q7', f'Observation {i} has {word_count} words, recommended max 50'))

    # Relations
    relations_elems = root.findall('relations')
    if relations_elems:
        relations = relations_elems[0].findall('relation')
        seen = set()
        for rel in relations:
            target = rel.get('target')
            rel_type = rel.get('type')

            if not target:
                errors.append(('R1', 'Relation missing target attribute'))
            if not rel_type:
                errors.append(('R1', 'Relation missing type attribute'))

            if rel_type and rel_type not in VALID_RELATION_TYPES:
                errors.append(('R2', f'Invalid relation type "{rel_type}"'))

            if target and not KEBAB_CASE.match(target):
                errors.append(('R3', f'Relation target "{target}" is not kebab-case'))

            if target and name and target == name:
                errors.append(('R4', f'Self-reference: target "{target}" equals memory name'))

            if target and rel_type:
                key = (target, rel_type)
                if key in seen:
                    errors.append(('R5', f'Duplicate relation: target="{target}" type="{rel_type}"'))
                seen.add(key)

    # Filesystem
    if filepath and name:
        if ' ' in name or any(c in name for c in '<>:"|?*\\'):
            errors.append(('F3', f'Name "{name}" contains filesystem-unsafe characters'))

    return errors


def validate_file(filepath):
    """Validate a memory file. Returns list of (rule_id, message) errors."""
    with open(filepath) as f:
        content = f.read()
    return validate(content, filepath, strict=True)


def validate_directory(dirpath):
    """Validate all .md files in a directory (excluding MEMORY.md).

    Returns dict of {filepath: [(rule_id, message), ...]}.
    Only includes files with errors.
    """
    results = {}
    for filename in sorted(os.listdir(dirpath)):
        if not filename.endswith('.md') or filename == 'MEMORY.md':
            continue
        filepath = os.path.join(dirpath, filename)
        if not os.path.isfile(filepath):
            continue
        errors = validate_file(filepath)
        if errors:
            results[filepath] = errors
    return results
