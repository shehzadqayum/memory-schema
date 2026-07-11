"""L0 (MEMORY.md) token budget enforcement and progressive disclosure.

Keeps MEMORY.md under a configurable token budget by evicting
the lowest-scoring entries. Evicted entries persist in L1+ stores;
only their L0 index visibility is removed.

Progressive disclosure: entries are grouped by type under section
headers. The index points to retrieval — it does not substitute.

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


# Category headers for progressive disclosure
_CATEGORY_ORDER = ['semantic', 'procedural', 'episodic']
_CATEGORY_HEADERS = {
    'semantic': '### Knowledge',
    'procedural': '### Procedures',
    'episodic': '### Session History',
}


def categorize_index(index_path, store_path=None):
    """Reorganize MEMORY.md entries under type-based category headers.

    Groups entries by memory type (semantic, procedural, episodic)
    with one-line section headers. Preserves the title line.
    Entries without a known type go under Knowledge (default).

    Args:
        index_path: Path to MEMORY.md.
        store_path: Path to store.jsonl (for type lookup).

    Returns:
        Number of entries categorized, or 0 if no changes.
    """
    if not os.path.exists(index_path):
        return 0

    with open(index_path, 'r') as f:
        content = f.read()

    entries, other_lines = parse_index_entries(content)
    if not entries:
        return 0

    # Look up types from store
    type_map = {}
    if store_path and os.path.exists(store_path):
        try:
            from memoryschema.store import MemoryStore
            store = MemoryStore(store_path)
            for name, _ in entries:
                entry = store.get(name)
                if entry:
                    type_map[name] = entry.get('type', 'semantic')
        except Exception:
            pass

    # Group entries by category
    categories = {cat: [] for cat in _CATEGORY_ORDER}
    for name, line in entries:
        entry_type = type_map.get(name, 'semantic')
        if entry_type not in categories:
            entry_type = 'semantic'
        categories[entry_type].append(line)

    # Reconstruct: title + non-entry lines first, then categories
    title_lines = [l for l in other_lines if l.strip() and not l.startswith('###')]
    output = []
    for line in title_lines:
        output.append(line)
    output.append('')

    for cat in _CATEGORY_ORDER:
        cat_entries = categories[cat]
        if cat_entries:
            output.append(_CATEGORY_HEADERS[cat])
            output.extend(cat_entries)
            output.append('')

    final = '\n'.join(output).strip() + '\n'

    with open(index_path, 'w') as f:
        f.write(final)

    return len(entries)


# --- L0 self-heal: rebuild MEMORY.md from the store ---------------------
#
# The append-only hook + evict-only budget could not keep MEMORY.md faithful: superseded/archived
# entries lingered (nothing removed them), evicted-or-never-added active entries never came back
# (no back-fill), and reconcile ignored L0 entirely. rebuild_index() regenerates the whole index
# from a store's ACTIVE set every time, so the index is idempotent and cannot drift. Called by the
# write hook (from the store it just wrote to) and by reconcile (from the authoritative JSONL).

_L0_DESC_WIDTH = 160


def _truncate_desc(desc, width=_L0_DESC_WIDTH):
    """One-line, width-bounded description for an L0 index line (collapses newlines/runs)."""
    desc = ' '.join((desc or '').split())
    return desc if len(desc) <= width else desc[:width].rstrip() + '…'


def _rank_key(e):
    """L0 ordering: importance DESC (salience), then name ASC (stable/deterministic). Store-agnostic
    (no dependency on the JSONL-only _score_entry), so it works for Neo4j or JSONL entries alike."""
    try:
        imp = int(e.get('importance') or 5)
    except (TypeError, ValueError):
        imp = 5
    return (-imp, e.get('name', ''))


def rebuild_index(index_path, entries=None, store_path=None,
                  token_budget=DEFAULT_TOKEN_BUDGET, title='## Project Memory'):
    """Regenerate MEMORY.md as a faithful L0 index of the store's ACTIVE entries (the self-heal).

    Idempotent: the index becomes exactly the active set — status-filtered (superseded/archived/
    quarantined excluded), de-duplicated, grouped by type (Knowledge/Procedures/Session History),
    ranked by importance, and bounded by the token budget (only the lowest-importance ACTIVE entries
    are dropped, and only when over budget — with an explicit note so truncation is never silent).

    Pass `entries` (a list of active entry dicts from whatever store the caller wrote to) OR a
    `store_path` (JSONL) to load them from. Returns {written, kept, dropped, tokens, total_active}.
    """
    if entries is None:
        if not store_path or not os.path.exists(store_path):
            return {'written': False, 'kept': 0, 'dropped': [], 'tokens': 0, 'total_active': 0}
        try:
            from memoryschema.store import MemoryStore
            entries = MemoryStore(store_path).list_all(include_inactive=False)
        except Exception:
            return {'written': False, 'kept': 0, 'dropped': [], 'tokens': 0, 'total_active': 0}

    # Active only (defensive — callers should already filter, but never trust a stale status).
    active = [e for e in entries if (e.get('status') or 'active') == 'active' and e.get('name')]
    ranked = sorted(active, key=_rank_key)
    total = len(active)

    def _line(e):
        name = e.get('name', '')
        return f'- [{name}]({name}.md) — {_truncate_desc(e.get("description", name))}'

    def _compose(kept, dropped_n):
        cats = {cat: [] for cat in _CATEGORY_ORDER}
        for e in kept:
            t = e.get('type', 'semantic')
            cats[t if t in cats else 'semantic'].append(_line(e))
        note = (f'{len(kept)} of {total} active memory entities shown (lowest-importance '
                f'{dropped_n} dropped for the L0 budget)' if dropped_n
                else f'{len(kept)} active memory entities')
        out = [title,
               f'{note} · auto-generated L0 index (regenerated by the write hook and '
               f'`memoryschema reconcile`) — full content in `memory/<name>.md` and the store.',
               '']
        for cat in _CATEGORY_ORDER:
            if cats[cat]:
                out.append(_CATEGORY_HEADERS[cat])
                out.extend(cats[cat])
                out.append('')
        return '\n'.join(out).strip() + '\n'

    kept = list(ranked)
    dropped = []
    # Evict the lowest-ranked (end of the importance-sorted list) until under budget.
    while kept and estimate_tokens(_compose(kept, len(dropped))) > token_budget:
        dropped.append(kept.pop().get('name', ''))
    content = _compose(kept, len(dropped))

    os.makedirs(os.path.dirname(index_path) or '.', exist_ok=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'written': True, 'kept': len(kept), 'dropped': dropped,
            'tokens': estimate_tokens(content), 'total_active': total}
