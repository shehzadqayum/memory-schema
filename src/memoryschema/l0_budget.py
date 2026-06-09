"""L0 (MEMORY.md) token budget enforcement.

Keeps MEMORY.md under a configurable token budget by evicting
the lowest-scoring entries. Evicted entries persist in L1+ stores;
only their L0 index visibility is removed.

Token estimation: chars / 4 (conservative approximation).
"""

import os
import re


DEFAULT_TOKEN_BUDGET = 2000


def estimate_tokens(text):
    """Estimate token count from text length (chars / 4)."""
    return len(text) // 4


def parse_index_entries(content):
    """Extract memory entry lines from MEMORY.md.

    Returns list of (name, full_line) tuples for entry lines,
    and list of other lines (headers, blank lines).
    """
    entries = []
    other_lines = []
    for line in content.split('\n'):
        m = re.match(r'^- \[([^\]]+)\]', line)
        if m:
            entries.append((m.group(1), line))
        else:
            other_lines.append(line)
    return entries, other_lines


def enforce_budget(index_path, store_path=None, token_budget=DEFAULT_TOKEN_BUDGET):
    """Enforce token budget on MEMORY.md by evicting lowest-scoring entries.

    Args:
        index_path: Path to MEMORY.md.
        store_path: Path to store.jsonl (for scoring). If None, evicts
            oldest entries (FIFO) instead of score-based.
        token_budget: Maximum estimated tokens for MEMORY.md.

    Returns:
        dict with keys: evicted (list of names), tokens_before, tokens_after.
    """
    if not os.path.exists(index_path):
        return {'evicted': [], 'tokens_before': 0, 'tokens_after': 0}

    with open(index_path, 'r') as f:
        content = f.read()

    tokens_before = estimate_tokens(content)
    if tokens_before <= token_budget:
        return {'evicted': [], 'tokens_before': tokens_before, 'tokens_after': tokens_before}

    entries, other_lines = parse_index_entries(content)

    # Score entries if store available
    scores = {}
    if store_path and os.path.exists(store_path):
        try:
            from memoryschema.store import MemoryStore
            store = MemoryStore(store_path)
            for name, _ in entries:
                entry = store.get(name)
                if entry:
                    scores[name] = store._score_entry(entry)
                else:
                    scores[name] = 0.0
        except Exception:
            pass

    # Sort entries by score (lowest first = evict first)
    if scores:
        entries.sort(key=lambda e: scores.get(e[0], 0.0))
    # else: FIFO order (first entries = oldest = evict first)

    # Evict until under budget
    evicted = []
    while entries:
        # Reconstruct content to check token count
        remaining_content = '\n'.join(other_lines + [e[1] for e in entries])
        if estimate_tokens(remaining_content) <= token_budget:
            break
        evicted_entry = entries.pop(0)  # remove lowest-scoring
        evicted.append(evicted_entry[0])

    # Rewrite MEMORY.md
    final_lines = other_lines + [e[1] for e in entries]
    final_content = '\n'.join(final_lines)
    # Clean up multiple blank lines
    final_content = re.sub(r'\n{3,}', '\n\n', final_content).strip() + '\n'

    with open(index_path, 'w') as f:
        f.write(final_content)

    tokens_after = estimate_tokens(final_content)
    return {
        'evicted': evicted,
        'tokens_before': tokens_before,
        'tokens_after': tokens_after,
    }
