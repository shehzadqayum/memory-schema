#!/usr/bin/env python3
"""
Example: Ingest Twitter archive into the memory system.

Reads YAML frontmatter markdown files from a Twitter archive,
converts each to a <memory:entity>, embeds in batches via Voyage AI,
and bulk-writes to the JSONL store.

Usage:
    python ingest_tweets.py --archive-root /path/to/archive --project my-project [--embed]

Requires: pip install memory-schema[all] pyyaml
"""

import argparse
import math
import os
import sys
import time
from xml.sax.saxutils import escape as xml_escape


def parse_tweet_file(filepath):
    """Parse a YAML frontmatter tweet file into a memory dict."""
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML required. pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.startswith('---'):
        return None

    end = text.find('\n---', 3)
    if end == -1:
        return None

    frontmatter = yaml.safe_load(text[4:end])
    body = text[end + 4:].strip()

    if not frontmatter or not frontmatter.get('id'):
        return None

    tweet_id = str(frontmatter['id'])
    name = f"tweet-{tweet_id}"
    author = frontmatter.get('author', 'unknown')
    date = str(frontmatter.get('date', ''))

    # Compute importance from engagement (log scale)
    replies = int(frontmatter.get('replies', 0) or 0)
    retweets = int(frontmatter.get('retweets', 0) or 0)
    likes = int(frontmatter.get('likes', 0) or 0)
    engagement = replies + retweets + likes
    max_engagement = 120_000
    if engagement > 0:
        importance = max(1, min(9, int(math.log(engagement + 1) / math.log(max_engagement + 1) * 9) + 1))
    else:
        importance = 1

    # Build observations
    observations = [
        f"Tweet by @{author}",
        f"Posted on {date}",
    ]
    if body:
        observations.append(f"Content: {body[:500]}")

    description = body[:120] if body else f"Tweet by @{author} on {date}"

    return {
        'name': name,
        'schema': 2,
        'type': 'semantic',
        'importance': importance,
        'description': description,
        'observations': observations,
    }


def compose_embedding_text(memory):
    """Compose text for embedding."""
    parts = [memory.get('description', '')]
    parts.extend(memory.get('observations', []))
    return ' '.join(parts).strip()


def main():
    parser = argparse.ArgumentParser(description='Ingest Twitter archive into memory system')
    parser.add_argument('--archive-root', required=True, help='Root directory of tweet .md files')
    parser.add_argument('--memory-dir', help='Output directory for memory files. Default: memory/tweets/')
    parser.add_argument('--store-path', help='JSONL store path. Default: memory/store.jsonl')
    parser.add_argument('--project', default='default', help='Project name')
    parser.add_argument('--embed', action='store_true', help='Embed via Voyage AI')
    parser.add_argument('--batch-size', type=int, default=50, help='Embedding batch size')
    parser.add_argument('--dry-run', action='store_true', help='Show stats without writing')
    args = parser.parse_args()

    memory_dir = args.memory_dir or 'memory/tweets'
    store_path = args.store_path or 'memory/store.jsonl'

    # Discover tweet files
    tweet_files = []
    for root, dirs, files in os.walk(args.archive_root):
        for f in files:
            if f.endswith('.md'):
                tweet_files.append(os.path.join(root, f))
    tweet_files.sort()
    print(f"Found {len(tweet_files)} tweet files")

    # Parse
    memories = []
    for filepath in tweet_files:
        memory = parse_tweet_file(filepath)
        if memory:
            memory['project'] = args.project
            memories.append(memory)

    print(f"Parsed {len(memories)} tweets")

    if args.dry_run:
        print("Dry run complete.")
        return

    # Write .md files
    os.makedirs(memory_dir, exist_ok=True)
    for memory in memories:
        filepath = os.path.join(memory_dir, f"{memory['name']}.md")
        obs_xml = '\n'.join(f'    <memory:observation>{xml_escape(o)}</memory:observation>'
                           for o in memory['observations'])
        content = f"""<memory:entity schema="2" name="{memory['name']}" type="semantic" importance="{memory['importance']}">
  <memory:description>{xml_escape(memory['description'])}</memory:description>
  <memory:observations>
{obs_xml}
  </memory:observations>
</memory:entity>
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"Wrote {len(memories)} .md files to {memory_dir}")

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
            try:
                vectors = embed_batch(texts)
                for m, v in zip(batch, vectors):
                    m['embedding'] = v
                embedded += len(batch)
            except Exception as e:
                print(f"  Batch {i // args.batch_size + 1} failed: {e}", file=sys.stderr)
            time.sleep(0.3)
            if (i + args.batch_size) % 500 < args.batch_size:
                print(f"  Embedded: {embedded}/{total}")

        print(f"Embedded: {embedded}/{total}")

    # Bulk upsert
    for memory in memories:
        store.upsert(memory)
    print(f"Upserted {len(memories)} entries to {store_path}")

    # Compute associations
    if args.embed:
        print("Computing associations...")
        assoc = store.compute_associations(k=10)
        print(f"Associations: {assoc} entries")

    print("Done.")


if __name__ == '__main__':
    main()
