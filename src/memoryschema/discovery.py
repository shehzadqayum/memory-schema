"""
Memory file discovery.

Finds .md files containing memory entities under a given path.
Pure Python, zero external dependencies.

Also provides frontmatter parsing and link extraction for
backward compatibility with legacy YAML-based memory files.
"""

import os
import re


def parse_frontmatter(text):
    """Parse YAML frontmatter from markdown text.

    Args:
        text: Raw markdown string.

    Returns:
        Tuple of (metadata_dict, body_string). If no frontmatter found,
        returns ({}, full text).
    """
    if not text.startswith('---'):
        return {}, text

    end = text.find('\n---', 3)
    if end == -1:
        return {}, text

    frontmatter_str = text[4:end]
    body = text[end + 4:].lstrip('\n')

    metadata = {}
    for line in frontmatter_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        colon = line.find(':')
        if colon == -1:
            continue
        key = line[:colon].strip()
        value = line[colon + 1:].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        metadata[key] = value

    return metadata, body


def extract_related(body):
    """Extract linked filenames from markdown body.

    Finds markdown links like [text](filename.md) and returns the
    target filenames. Only extracts .md links (not URLs).

    Args:
        body: Markdown body text.

    Returns:
        List of linked filenames.
    """
    links = re.findall(r'\[([^\]]*)\]\(([^)]+\.md)\)', body)
    filenames = []
    for _text, target in links:
        if target.startswith(('http://', 'https://', '/')):
            continue
        filenames.append(target)
    return filenames


def discover_memory_files(base_path):
    """Discover all memory .md files under a base path.

    Walks the directory tree and returns all .md files, excluding
    MEMORY.md (the index file).

    Args:
        base_path: Root directory to search.

    Returns:
        Sorted list of absolute paths to memory .md files.
    """
    memory_files = []

    if not os.path.isdir(base_path):
        return memory_files

    for root, _dirs, files in os.walk(base_path):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            if fname == 'MEMORY.md':
                continue
            memory_files.append(os.path.join(root, fname))

    return sorted(memory_files)
