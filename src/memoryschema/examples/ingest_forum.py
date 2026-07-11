#!/usr/bin/env python3
"""
Example: Ingest web forum archive into the memory system.

Reads HTML forum post files (e.g., from SiteSucker), extracts post
content, creates a v5 memory entity per post (via write_index.create_entity_file),
embeds in batches, and bulk-writes to the JSONL store.

Usage:
    python ingest_forum.py --forum-root /path/to/forum/posts --project my-project [--embed]

Requires: pip install memory-schema[all] beautifulsoup4
"""

import argparse
import html
import math
import os
import re
import sys
import time


def parse_forum_post(filepath, primary_author=None):
    """Parse an HTML forum post file into a memory dict.

    Args:
        filepath: Path to HTML file.
        primary_author: Username of the primary/authoritative poster
                       (gets importance boost).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("Error: beautifulsoup4 required. pip install beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Extract post content (adapt selectors to your forum's HTML structure)
    content_elem = soup.find('div', class_='post-content') or soup.find('div', class_='message')
    if not content_elem:
        # Fallback: extract all text
        content_elem = soup.find('body') or soup

    text = content_elem.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()

    if not text or len(text) < 10:
        return None

    # Extract metadata (adapt to your forum's structure)
    author_elem = soup.find('a', class_='author') or soup.find('span', class_='username')
    author = author_elem.get_text(strip=True) if author_elem else 'unknown'

    date_elem = soup.find('time') or soup.find('span', class_='date')
    date = date_elem.get_text(strip=True) if date_elem else ''

    thread_elem = soup.find('h1') or soup.find('title')
    thread = thread_elem.get_text(strip=True) if thread_elem else ''

    # Derive name from filepath
    basename = os.path.splitext(os.path.basename(filepath))[0]
    name = f"forum-{basename}"
    name = re.sub(r'[^a-z0-9-]', '-', name.lower())
    name = re.sub(r'-+', '-', name).strip('-')

    # Importance
    is_primary = primary_author and author.lower() == primary_author.lower()
    importance = 9 if is_primary else 5

    # Build observations
    observations = [
        f"Post by {author}",
        f"Posted on {date}" if date else None,
        f"Thread: {thread}" if thread else None,
        f"Message: {text[:500]}",
    ]
    observations = [o for o in observations if o]

    # Continuation observations for long posts
    if len(text) > 500:
        for i in range(500, min(len(text), 2000), 500):
            observations.append(f"Message (cont): {text[i:i+500]}")

    description = text[:120]

    return {
        'name': name,
        'schema': 5,
        'type': 'semantic',
        'provenance': 'ingested',
        'importance': importance,
        'description': description,
        'observations': observations,
    }


def compose_embedding_text(memory, max_chars=2000):
    """Compose text for embedding."""
    parts = [memory.get('description', '')]
    parts.extend(memory.get('observations', []))
    return ' '.join(parts).strip()[:max_chars]


def main():
    parser = argparse.ArgumentParser(description='Ingest forum archive into memory system')
    parser.add_argument('--forum-root', required=True, help='Root directory of forum HTML files')
    parser.add_argument('--memory-dir', help='Output directory. Default: memory/forum/')
    parser.add_argument('--store-path', help='JSONL store path. Default: memory/store.jsonl')
    parser.add_argument('--project', default='default', help='Project name')
    parser.add_argument('--primary-author', help='Username of authoritative poster (gets importance boost)')
    parser.add_argument('--embed', action='store_true', help='Embed via Voyage AI')
    parser.add_argument('--batch-size', type=int, default=20, help='Embedding batch size')
    parser.add_argument('--dry-run', action='store_true', help='Show stats without writing')
    args = parser.parse_args()

    memory_dir = args.memory_dir or 'memory/forum'
    store_path = args.store_path or 'memory/store.jsonl'

    # Discover HTML files
    html_files = []
    for root, dirs, files in os.walk(args.forum_root):
        for f in files:
            if f.endswith(('.html', '.htm')):
                html_files.append(os.path.join(root, f))
    html_files.sort()
    print(f"Found {len(html_files)} HTML files")

    # Parse
    memories = []
    for filepath in html_files:
        memory = parse_forum_post(filepath, args.primary_author)
        if memory:
            memory['project'] = args.project
            memories.append(memory)

    print(f"Parsed {len(memories)} forum posts")

    if args.dry_run:
        primary_count = sum(1 for m in memories if m['importance'] >= 8)
        print(f"Primary author posts: {primary_count}")
        print("Dry run complete.")
        return

    # Write .md files (v5 — create_entity_file serializes + validates; no manual XML or escaping)
    from memoryschema.write_index import create_entity_file
    os.makedirs(memory_dir, exist_ok=True)
    written = 0
    for memory in memories:
        filepath = os.path.join(memory_dir, f"{memory['name']}.md")
        if os.path.exists(filepath):
            continue  # create_entity_file refuses to overwrite an existing entity (skip already-ingested)
        create_entity_file(filepath, memory['name'], memory['description'], memory['observations'],
                           importance=memory.get('importance'), mtype=memory.get('type'),
                           project=memory.get('project'))
        written += 1

    print(f"Wrote {written} v5 .md files to {memory_dir}")

    # Embed + store
    from memoryschema.store import MemoryStore
    store = MemoryStore(store_path)

    if args.embed:
        try:
            from memoryschema.embeddings import embed_batch
        except ImportError:
            print("Error: voyageai required. pip install memory-schema[embeddings]", file=sys.stderr)
            return

        total = len(memories)
        embedded = 0
        for i in range(0, total, args.batch_size):
            batch = memories[i:i + args.batch_size]
            texts = [compose_embedding_text(m) for m in batch]
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    vectors = embed_batch(texts)
                    for m, v in zip(batch, vectors):
                        m['embedding'] = v
                    embedded += len(batch)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = 2.0 * (2 ** attempt)
                        print(f"  Retry {attempt + 1} after {delay}s: {e}")
                        time.sleep(delay)
                    else:
                        print(f"  Batch failed: {e}", file=sys.stderr)
            time.sleep(0.3)
            if (i + args.batch_size) % 200 < args.batch_size:
                print(f"  Embedded: {embedded}/{total}")

        print(f"Embedded: {embedded}/{total}")

    for memory in memories:
        store.upsert(memory)
    print(f"Upserted {len(memories)} entries to {store_path}")

    if args.embed:
        print("Computing associations...")
        assoc = store.compute_associations(k=10)
        print(f"Associations: {assoc} entries")

    print("Done.")


if __name__ == '__main__':
    main()
