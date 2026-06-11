"""Numeric contradiction probe for the write gate (stage 5).

Detects when a candidate entity asserts a different quantity for the same
unit noun as an existing active entity. Routes to QUARANTINE (never REJECT)
because the extractor is heuristic.

Claim key design: (unit, qualifier) — two claims compare only when both
elements match exactly. "5 tests added" (test, added) never collides with
"472 tests passing" (test, passing) or bare "472 tests" (test, None).
This is deliberately conservative: the probe under-fires rather than
over-quarantines. The qualifier captures only the single token following
the unit noun, so "472 tests currently passing" keys as (test, currently)
not (test, passing). A future operator examining a missed-but-obvious
contradiction should find this explanation here.

Extension point: compare() takes the neighbour set as an argument, so
an alternative neighbour source (e.g. a second embedding space) can be
substituted later without modifying the gate. Building any such second
space is explicitly out of scope.
"""

import re

# Stoplist: units to ignore
_STOPLIST = frozenset({'percent', 'version'})

# Pattern 1: "472 tests passing" → (472, test, passing)
_PAT_NUM_UNIT = re.compile(
    r'(\d[\d,]*(?:\.\d+)?)\s+([a-z][a-z_-]{2,})(?:\s+([a-z]{2,}))?'
)
# Pattern 2: "tests: 472" → (472, test, None)
_PAT_UNIT_NUM = re.compile(
    r'([a-z][a-z_-]{2,})\s*[:=]\s*(\d[\d,]*(?:\.\d+)?)'
)
# 4-digit years
_YEAR_RE = re.compile(r'^(19|20)\d{2}$')
# Version tokens
_VERSION_RE = re.compile(r'^v\d')


def _normalize_unit(unit):
    """Normalize a unit noun: lowercase, strip trailing punctuation, singularize trailing s."""
    unit = unit.lower().rstrip('.,;:!?')
    if unit.endswith('s') and len(unit) > 3:
        unit = unit[:-1]
    return unit


def _parse_number(s):
    """Parse a number string, stripping commas."""
    return float(s.replace(',', ''))


def extract_claims(text):
    """Extract numeric claims from text.

    Returns list of (quantity, unit, qualifier) tuples.
    Qualifier is the single token after the unit, or None.
    """
    if not text:
        return []

    claims = []

    # Pattern 1: number unit [qualifier]
    for m in _PAT_NUM_UNIT.finditer(text):
        num_str, unit_raw, qualifier = m.group(1), m.group(2), m.group(3)
        unit = _normalize_unit(unit_raw)
        if unit in _STOPLIST:
            continue
        if _YEAR_RE.match(num_str):
            continue
        if _VERSION_RE.match(unit):
            continue
        try:
            quantity = _parse_number(num_str)
        except ValueError:
            continue
        claims.append((quantity, unit, qualifier))

    # Pattern 2: unit: number (no qualifier)
    for m in _PAT_UNIT_NUM.finditer(text):
        unit_raw, num_str = m.group(1), m.group(2)
        unit = _normalize_unit(unit_raw)
        if unit in _STOPLIST:
            continue
        if _YEAR_RE.match(num_str):
            continue
        if _VERSION_RE.match(unit):
            continue
        try:
            quantity = _parse_number(num_str)
        except ValueError:
            continue
        # Avoid duplicates from overlapping patterns
        if not any(q == quantity and u == unit for q, u, _ in claims):
            claims.append((quantity, unit, None))

    return claims


def extract_entity_claims(entity):
    """Extract all claims from an entity's description + observations."""
    texts = [entity.get('description', '')]
    for obs in entity.get('observations', []):
        texts.append(str(obs))
    all_claims = []
    for text in texts:
        all_claims.extend(extract_claims(text))
    return all_claims


def compare(candidate_claims, neighbour_entities):
    """Compare candidate claims against neighbour entities.

    Pure function — no store access. The gate fetches neighbours
    and passes them here.

    Returns list of hit dicts:
        {unit, qualifier, candidate_value, neighbour_name, neighbour_value}
    """
    hits = []
    for entity in neighbour_entities:
        entity_claims = extract_entity_claims(entity)
        entity_name = entity.get('name', '?')

        # Check for declared CONTRADICTS or SUPERSEDES → bypass
        relations = entity.get('relations', [])
        # (bypass is checked per-entity by the caller, not here)

        for c_qty, c_unit, c_qual in candidate_claims:
            for e_qty, e_unit, e_qual in entity_claims:
                if c_unit == e_unit and c_qual == e_qual and c_qty != e_qty:
                    hits.append({
                        'unit': c_unit,
                        'qualifier': c_qual,
                        'candidate_value': c_qty,
                        'neighbour_name': entity_name,
                        'neighbour_value': e_qty,
                    })
    return hits
