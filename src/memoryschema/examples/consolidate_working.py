#!/usr/bin/env python3
"""
Example: Consolidate working memory files into clusters.

Merges iterative working memory files (many small entities about
the same topic) into consolidated cluster entities.

Usage:
    python consolidate_working.py --memory-dir memory/ [--dry-run]

Requires: pip install memory-schema
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from xml.sax.saxutils import escape as xml_escape

from memoryschema.tags import parse_memory_file


def group_by_prefix(memory_dir):
    """Group memory files by name prefix (before the last hyphen-number)."""
    groups = defaultdict(list)
    for f in sorted(os.listdir(memory_dir)):
        if not f.endswith('.md') or f == 'MEMORY.md':
            continue
        filepath = os.path.join(memory_dir, f)
        memory = parse_memory_file(filepath)
        if memory is None:
            continue
        # Group by topic prefix (remove trailing numbers/hyphens)
        name = memory['name']
        prefix = re.sub(r'-\d+$', '', name)
        groups[prefix].append(memory)
    return groups


def merge_cluster(memories, cluster_name):
    """Merge multiple memories into one consolidated entity."""
    # Use highest importance
    importance = max(m.get('importance') or 5 for m in memories)

    # Merge observations (dedup)
    all_obs = []
    seen = set()
    for m in memories:
        for obs in m.get('observations', []):
            if obs not in seen:
                all_obs.append(obs)
                seen.add(obs)

    # Use the best description (longest)
    descriptions = [m.get('description', '') for m in memories]
    description = max(descriptions, key=len) if descriptions else cluster_name

    # Merge relations (dedup by target+type)
    all_rels = []
    seen_rels = set()
    for m in memories:
        for rel in m.get('relations', []):
            key = (rel.get('target'), rel.get('type'))
            if key not in seen_rels:
                all_rels.append(rel)
                seen_rels.add(key)

    # Use latest reasoning
    reasonings = [m.get('reasoning') for m in memories if m.get('reasoning')]
    reasoning = reasonings[-1] if reasonings else None

    # Use latest prompt
    prompts = [m.get('prompt') for m in memories if m.get('prompt')]
    prompt = prompts[-1] if prompts else None

    return {
        'name': cluster_name,
        'schema': 2,
        'type': memories[0].get('type', 'semantic'),
        'importance': importance,
        'description': description[:120],
        'observations': all_obs,
        'reasoning': reasoning,
        'prompt': prompt,
        'relations': all_rels,
    }


def write_entity(memory, output_dir):
    """Write a memory entity to a .md file."""
    filepath = os.path.join(output_dir, f"{memory['name']}.md")

    obs_xml = ""
    if memory.get('observations'):
        obs_lines = '\n'.join(f'    <memory:observation>{xml_escape(o)}</memory:observation>'
                              for o in memory['observations'])
        obs_xml = f"\n  <memory:observations>\n{obs_lines}\n  </memory:observations>"

    prompt_xml = ""
    if memory.get('prompt'):
        prompt_xml = f"\n  <memory:prompt>{xml_escape(memory['prompt'])}</memory:prompt>"

    reasoning_xml = ""
    if memory.get('reasoning'):
        reasoning_xml = f"\n  <memory:reasoning>{xml_escape(memory['reasoning'])}</memory:reasoning>"

    rels_xml = ""
    if memory.get('relations'):
        rel_lines = '\n'.join(
            f'    <memory:relation target="{r["target"]}" type="{r["type"]}"/>'
            for r in memory['relations'] if r.get('target') and r.get('type')
        )
        if rel_lines:
            rels_xml = f"\n  <memory:relations>\n{rel_lines}\n  </memory:relations>"

    imp = memory.get('importance', 5)
    typ = memory.get('type', 'semantic')

    content = f"""<memory:entity schema="3" name="{memory['name']}" type="{typ}" importance="{imp}">
  <memory:description>{xml_escape(memory['description'])}</memory:description>{obs_xml}{prompt_xml}{reasoning_xml}{rels_xml}
</memory:entity>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description='Consolidate working memory files')
    parser.add_argument('--memory-dir', required=True, help='Directory containing memory .md files')
    parser.add_argument('--output-dir', help='Output directory for consolidated files. Default: same as memory-dir')
    parser.add_argument('--min-group', type=int, default=2, help='Minimum group size to consolidate. Default: 2')
    parser.add_argument('--dry-run', action='store_true', help='Show groups without consolidating')
    args = parser.parse_args()

    output_dir = args.output_dir or args.memory_dir

    groups = group_by_prefix(args.memory_dir)
    print(f"Found {len(groups)} prefix groups from {sum(len(v) for v in groups.values())} files")

    consolidatable = {k: v for k, v in groups.items() if len(v) >= args.min_group}
    print(f"Groups with {args.min_group}+ files: {len(consolidatable)}")

    if args.dry_run:
        for prefix, memories in sorted(consolidatable.items()):
            print(f"  {prefix}: {len(memories)} files → 1 consolidated")
        print("Dry run complete.")
        return

    os.makedirs(output_dir, exist_ok=True)
    consolidated = 0
    for prefix, memories in consolidatable.items():
        merged = merge_cluster(memories, prefix)
        write_entity(merged, output_dir)
        consolidated += 1

    # Copy singletons unchanged
    singletons = {k: v for k, v in groups.items() if len(v) < args.min_group}
    for prefix, memories in singletons.items():
        for m in memories:
            write_entity(m, output_dir)

    print(f"Consolidated {consolidated} groups.")
    print(f"Copied {sum(len(v) for v in singletons.values())} singletons.")


if __name__ == '__main__':
    main()
