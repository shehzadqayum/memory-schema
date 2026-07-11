"""
Memory schema validator.

Validates memory entity files against the schema specification. `validate()` format-dispatches on
`is_v5_content`: a v5 (frontmatter) file is validated by `_validate_v5`, a v4 XML file by the legacy path.

Validation rules (rule IDs shared across both formats; the v4 XML path below, v5 in `_validate_v5`):
  V1-V12: Structure (V8 retired; the filename-match check is emitted as V3)
  R1-R6:  Relations (attributes, types, self-reference, duplicates, referential integrity)
          — SUPERSEDES cycle detection (R7) lives in the store, not here
  F3:     Filesystem (filesystem-safe name characters)
  Q1-Q2, Q6-Q8: Content quality (strict mode only)
"""

import os
import re
import xml.etree.ElementTree as ET


from memoryschema.config import (
    VALID_TYPES, VALID_STATUSES,
    VALID_RELATION_TYPES, DEPRECATED_RELATION_TYPES, ALL_RELATION_TYPES,
)
from memoryschema.entity_schema import KEBAB_CASE, V4_XML_SCHEMA_VERSION  # authority: name grammar + v4 attr bound


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


def validate(content, filepath=None, strict=False, known_names=None):
    """Validate memory file content against schema rules.

    Args:
        content: File content as string.
        filepath: Optional filepath for filesystem rules (F1, F3).
        strict: If True, include content quality checks (Q1, Q2, Q6, Q7, Q8, Q9).
        known_names: Optional set of existing memory names for R6
            (referential integrity). If provided, relation targets
            are checked against this set.

    Returns:
        List of (rule_id, message) tuples for each validation failure.
        Empty list means the file is valid.
    """
    # Format dispatch: v5 (frontmatter+markdown) validates via the parsed dict; v4 XML falls through below.
    # Without this, a v5 file returns a spurious V1 "no entity" and bypasses every V/R/Q rule (schema-split B1).
    from memoryschema.format_v5 import is_v5_content
    if is_v5_content(content):
        return _validate_v5(content, filepath=filepath, strict=strict, known_names=known_names)

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

    # V10: the legacy v4-XML `schema=` attribute must be within the v4 range (this path is v4-only; v5 is a
    # different format, never a `schema="5"` XML file, so the bound stays the v4 marker, not the current version)
    schema_str = root.get('schema')
    if schema_str is not None:
        try:
            schema_ver = int(schema_str)
            if schema_ver < 1 or schema_ver > V4_XML_SCHEMA_VERSION:
                errors.append(('V10', f'Schema version {schema_ver} out of range, must be 1-{V4_XML_SCHEMA_VERSION}'))
        except ValueError:
            errors.append(('V10', f'Schema "{schema_str}" is not a valid integer'))

    # V3: name matches filename
    if filepath and name:
        expected = f'{name}.md'
        actual = os.path.basename(filepath)
        if actual != expected:
            errors.append(('V3', f'Filename "{actual}" does not match name "{name}" (expected "{expected}")'))

    # V4: type is a non-empty string (optional, free-form — no predefined values enforced)
    type_val = root.get('type')
    if type_val is not None and not type_val.strip():
        errors.append(('V4', 'Type attribute is present but empty'))

    # V5: importance is integer 1-10 (optional field)
    importance_str = root.get('importance')
    if importance_str is not None:
        try:
            importance = int(importance_str)
            if importance < 1 or importance > 10:
                errors.append(('V5', f'Importance {importance} out of range, must be 1-10'))
        except ValueError:
            errors.append(('V5', f'Importance "{importance_str}" is not a valid integer'))

    # V12: confidence is integer 1-10 (optional field)
    confidence_str = root.get('confidence')
    if confidence_str is not None:
        try:
            confidence = int(confidence_str)
            if confidence < 1 or confidence > 10:
                errors.append(('V12', f'Confidence {confidence} out of range, must be 1-10'))
        except ValueError:
            errors.append(('V12', f'Confidence "{confidence_str}" is not a valid integer'))

    # V11: status is valid (optional field, v3)
    status_val = root.get('status')
    if status_val and status_val not in VALID_STATUSES:
        errors.append(('V11', f'Invalid status "{status_val}", must be one of: {", ".join(sorted(VALID_STATUSES))}'))

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

        # Q8: reasoning length (affects embedding quality)
        reasoning_elem = root.find('reasoning')
        if reasoning_elem is not None and reasoning_elem.text:
            reasoning_words = len(reasoning_elem.text.split())
            if reasoning_words > 500:
                errors.append(('Q8', f'Reasoning has {reasoning_words} words, recommended max 500'))


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

            if rel_type and rel_type not in ALL_RELATION_TYPES:
                errors.append(('R2', f'Invalid relation type "{rel_type}"'))
            elif rel_type and rel_type in DEPRECATED_RELATION_TYPES:
                errors.append(('R2', f'Deprecated relation type "{rel_type}" — use project field for hierarchy'))

            if target and not KEBAB_CASE.match(target):
                errors.append(('R3', f'Relation target "{target}" is not kebab-case'))

            if target and name and target == name:
                errors.append(('R4', f'Self-reference: target "{target}" equals memory name'))

            if target and rel_type:
                key = (target, rel_type)
                if key in seen:
                    errors.append(('R5', f'Duplicate relation: target="{target}" type="{rel_type}"'))
                seen.add(key)

            # R6: referential integrity (warning in standard, error in strict)
            if target and known_names is not None and target not in known_names:
                errors.append(('R6', f'Relation target "{target}" does not exist in known memories'))

    # Filesystem
    if filepath and name:
        if ' ' in name or any(c in name for c in '<>:"|?*\\'):
            errors.append(('F3', f'Name "{name}" contains filesystem-unsafe characters'))

    return errors


def _frontmatter_scalar(content, key):
    """Return the raw (quote-stripped) value of a top-level frontmatter scalar `key`, scanning ONLY the leading
    `---` fence block (never the body), or None if absent. Used to recover a value the v5 parser dropped."""
    lines = content.lstrip('﻿').lstrip().splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    prefix = key + ':'
    for line in lines[1:]:
        s = line.strip()
        if s == '---':
            break
        if s.startswith(prefix) and not line.startswith((' ', '-')):
            return s[len(prefix):].strip().strip('"').strip("'")
    return None


def _validate_v5(content, filepath=None, strict=False, known_names=None):
    """Validate a v5 (frontmatter+markdown) entity against the semantic invariants.

    v5 well-formedness is PARSE-BASED — a file that parses is structurally sound, so the XML-structural rules
    (V1 root, V6 description, V9 closed-tags) do not apply; a file that declares `schema: 5` but won't parse
    is corruption. This runs the content/relation/quality rules on the parsed dict, reusing the v4 rule IDs so
    every consumer sees one vocabulary. Grammars come from entity_schema (the authority), same as the v4 path."""
    from memoryschema.format_v5 import parse_v5_content
    mem = parse_v5_content(content, filepath=filepath)
    if mem is None:
        return [('V1', 'v5 entity failed to parse (unterminated fence or missing `schema: 5`)')]

    errors = []
    name = mem.get('name')   # parse_v5_content guarantees a truthy name (else it returns None -> V1 above)

    # V3: name matches filename
    if filepath and name:
        expected = f'{name}.md'
        actual = os.path.basename(filepath)
        if actual != expected:
            errors.append(('V3', f'Filename "{actual}" does not match name "{name}" (expected "{expected}")'))

    # V5: importance 1-10. The parser SILENTLY DROPS a non-integer importance (so it's absent from `mem`); for
    # parity with the v4 path — which flags a non-integer importance — re-scan the raw frontmatter when the key
    # is absent, and flag a present-but-non-integer value.
    if 'importance' in mem:
        imp = mem['importance']
        if not isinstance(imp, int) or imp < 1 or imp > 10:
            errors.append(('V5', f'Importance {imp} out of range, must be 1-10'))
    else:
        raw_imp = _frontmatter_scalar(content, 'importance')
        if raw_imp is not None:
            try:
                int(raw_imp)
            except ValueError:
                errors.append(('V5', f'Importance "{raw_imp}" is not a valid integer'))

    # V11: status is valid
    status_val = mem.get('status')
    if status_val and status_val not in VALID_STATUSES:
        errors.append(('V11', f'Invalid status "{status_val}", must be one of: {", ".join(sorted(VALID_STATUSES))}'))

    # Content quality (strict mode)
    if strict:
        if name and not KEBAB_CASE.match(name):
            errors.append(('Q1', f'Name "{name}" is not kebab-case'))
        desc = mem.get('description') or ''
        if '\n' in desc:
            errors.append(('Q2', 'Description contains newlines'))
        if len(desc) > 120:
            errors.append(('Q2', f'Description is {len(desc)} chars, max 120'))
        # Q6/Q7 apply to real observations, NOT chain `## Log` steps (the parser flattens log into
        # observations; a chain legitimately carries many steps). observations == obs + log, so the
        # leading slice is the true observation set.
        log = mem.get('log') or []
        all_obs = mem.get('observations') or []
        real_obs = all_obs[:len(all_obs) - len(log)] if len(all_obs) >= len(log) else all_obs
        if len(real_obs) > 10:
            errors.append(('Q6', f'{len(real_obs)} observations, recommended max 10'))
        for i, o in enumerate(real_obs, 1):
            wc = len(str(o).split())
            if wc > 50:
                errors.append(('Q7', f'Observation {i} has {wc} words, recommended max 50'))
        reasoning = mem.get('reasoning')
        if reasoning and len(reasoning.split()) > 500:
            errors.append(('Q8', f'Reasoning has {len(reasoning.split())} words, recommended max 500'))

    # Relations (R1-R6) — parse-liberally/validate-strictly: the parser accepts a superset of the target
    # grammar, so a non-kebab target reaches here and R3 flags it (rather than being silently dropped).
    seen = set()
    for rel in (mem.get('relations') or []):
        target = rel.get('target')
        rel_type = rel.get('type')
        if not target:
            errors.append(('R1', 'Relation missing target attribute'))
        if not rel_type:
            errors.append(('R1', 'Relation missing type attribute'))
        if rel_type and rel_type not in ALL_RELATION_TYPES:
            errors.append(('R2', f'Invalid relation type "{rel_type}"'))
        elif rel_type and rel_type in DEPRECATED_RELATION_TYPES:
            errors.append(('R2', f'Deprecated relation type "{rel_type}" — use project field for hierarchy'))
        if target and not KEBAB_CASE.match(target):
            errors.append(('R3', f'Relation target "{target}" is not kebab-case'))
        if target and name and target == name:
            errors.append(('R4', f'Self-reference: target "{target}" equals memory name'))
        if target and rel_type:
            key = (target, rel_type)
            if key in seen:
                errors.append(('R5', f'Duplicate relation: target="{target}" type="{rel_type}"'))
            seen.add(key)
        if target and known_names is not None and target not in known_names:
            errors.append(('R6', f'Relation target "{target}" does not exist in known memories'))

    # F3: filesystem-safe name
    if filepath and name:
        if ' ' in name or any(c in name for c in '<>:"|?*\\'):
            errors.append(('F3', f'Name "{name}" contains filesystem-unsafe characters'))

    return errors


def validate_file(filepath):
    """Validate a memory file. Returns list of (rule_id, message) errors."""
    # Pin utf-8 (matching tags.parse_memory_file); the platform default (cp1252
    # on Windows without PYTHONUTF8) raises UnicodeDecodeError on common
    # typography and aborts validate_directory on the first such file.
    with open(filepath, encoding="utf-8") as f:
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
