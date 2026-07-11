"""
entity_schema.py — the single machine-readable AUTHORITY for the memory entity schema.

This module is the source of truth for what a memory *entity* is: its frontmatter fields, its enums, its
name/key grammars, and (progressively) its invariants. The harness — ``config.py``, ``validator.py``,
``format_v5.py`` and the docs — CONFORMS to this module, never the other way around
(see docs/schema-specification.md). Kept a **leaf** module on purpose: it imports nothing else from
``memoryschema`` so no import cycles are possible.

NOTE: distinct from ``schema.py``, which defines the Neo4j database DDL. This is the *entity* schema.

Drift protection: the harness single-sources these definitions (imports them here), and
``tests/test_schema_conformance.py`` asserts the behavior + doc-generation stay in agreement. The machine
reference tables in the prose spec are emitted by ``render_reference_tables()`` below.
"""
import re

# ── Version ────────────────────────────────────────────────────────────────────────────────────────
# The current authored entity format is v5 (YAML frontmatter + markdown body). v4 XML is legacy: parsed on
# read + migrated, never newly authored.
CURRENT_ENTITY_FORMAT = 5    # entities are authored in v5
# ``SCHEMA_VERSION`` is the current entity-schema version — it now tracks the current format (schema-split B4;
# previously it was pinned at the legacy v4 marker, misreporting the schema as v4). The v4-XML ``schema="N"``
# attribute keeps its OWN upper bound below (a v4 file is not "schema 5" — v5 is a different format, not XML),
# used solely by the validator's V10 range check.
SCHEMA_VERSION = CURRENT_ENTITY_FORMAT        # = 5, the current schema version
V4_XML_SCHEMA_VERSION = 4                      # legacy v4-XML `schema=` attribute upper bound (V10 only)

# ── Enums (semantics documented in docs/schema-specification.md §3.5/§3.6) ───────────────────────────
VALID_TYPES = frozenset({'semantic', 'episodic', 'procedural'})
VALID_STATUSES = frozenset({'active', 'superseded', 'archived', 'quarantined'})
# Each relation type carries distinct machinery (documented in the schema spec): SUPERSEDES = status-flip +
# L0 removal + cycle detection; CONTRADICTS = symmetric edge + gate probe-bypass; MITIGATES = x0.95 score
# dampening; USES/INFORMS = citation telemetry.
VALID_RELATION_TYPES = frozenset({
    'USES', 'MODIFIES', 'SUPERSEDES', 'DEPENDS_ON', 'INFORMS', 'CONTRADICTS', 'MITIGATES',
})
# Deprecated: hierarchy is the ``project`` field, not relation edges. Accepted on read, warned on write.
DEPRECATED_RELATION_TYPES = frozenset({'PARENT_OF', 'CHILD_OF'})
ALL_RELATION_TYPES = VALID_RELATION_TYPES | DEPRECATED_RELATION_TYPES

# ── Grammars — ONE canonical definition each ─────────────────────────────────────────────────────────
# Entity NAME and relation TARGET are the same grammar: strict kebab-case (the live corpus is 100% kebab).
NAME_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
# Back-compat alias: validator.py historically named this KEBAB_CASE.
KEBAB_CASE = NAME_RE
# Fact KEY (the temporal ``key:`` field) is a SEPARATE grammar: kebab segments joined by dots,
# e.g. ``memory-schema.multi-space-status``. Distinct from names/targets, which never contain dots.
KEY_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*(\.[a-z0-9]+(-[a-z0-9]+)*)+$')

# Note on parse-liberally / validate-strictly (Postel): the v5 line PARSER (``format_v5._REL_RE``) is a
# deliberate SUPERSET of NAME_RE — it accepts a wider target charset so a legal edge is never silently dropped
# on parse — while the VALIDATOR enforces NAME_RE. The parser tightens only once name-creation is enforced
# (follow-up B-series). test_schema_conformance asserts exactly this relationship.

# ── Frontmatter fields (the v5 structured/machine layer) ─────────────────────────────────────────────
FRONTMATTER_FIELDS = (
    'schema', 'name', 'type', 'status', 'importance', 'project', 'key',
    'valid_from', 'superseded_at', 'superseded_by', 'promoted_to', 'relations',
)


def render_reference_tables():
    """Emit the machine-checkable reference tables (enums + grammars + fields) as markdown. The prose schema
    spec (docs/schema-specification.md) and the on-demand rule embed this output, and
    tests/test_schema_conformance.py regenerates + diffs it — so those doc sections cannot drift from code."""
    def _set(s):
        return ' · '.join(f'`{v}`' for v in sorted(s))
    lines = [
        f'- **Entity format:** v{CURRENT_ENTITY_FORMAT} (current) · v4 XML (legacy, read-only)',
        f'- **Types:** {_set(VALID_TYPES)}',
        f'- **Statuses:** {_set(VALID_STATUSES)}',
        f'- **Relation types:** {_set(VALID_RELATION_TYPES)}  ·  deprecated: {_set(DEPRECATED_RELATION_TYPES)}',
        f'- **Name / relation-target grammar:** `{NAME_RE.pattern}` (strict kebab-case)',
        f'- **Fact-key grammar:** `{KEY_RE.pattern}` (kebab segments joined by dots)',
        f'- **Frontmatter fields:** {" · ".join(f"`{f}`" for f in FRONTMATTER_FIELDS)}',
    ]
    return '\n'.join(lines)
