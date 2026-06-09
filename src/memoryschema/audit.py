"""Append-only audit log for memory mutations.

Records every create/upsert/archive/delete/status-change to
memory/audit.jsonl with timestamp, operation, fields changed,
and prior value hashes.

One line per mutation. Never modified or truncated — append only.
"""

import hashlib
import json
import os
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hash_value(value):
    """SHA-256 hash of a string value (for prior content tracking)."""
    if value is None:
        return None
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:16]


def _diff_fields(existing, new_dict):
    """Compute which fields changed between existing and new entry.

    Returns dict of {field: {prior_hash, new_hash}} for changed fields.
    """
    tracked_fields = (
        'description', 'type', 'status', 'provenance', 'importance',
        'body', 'prompt', 'reasoning', 'source', 'project',
    )
    changes = {}
    for field in tracked_fields:
        old_val = existing.get(field)
        new_val = new_dict.get(field)
        if new_val is not None and old_val != new_val:
            changes[field] = {
                'prior_hash': _hash_value(old_val),
                'new_hash': _hash_value(new_val),
            }
    return changes


def log_mutation(audit_path, operation, name, changes=None, prior_entry=None):
    """Append a mutation record to the audit log.

    Args:
        audit_path: Path to audit.jsonl file.
        operation: One of 'create', 'upsert', 'archive', 'delete',
                   'status-change'.
        name: Memory entity name.
        changes: Optional dict of field changes (from _diff_fields).
        prior_entry: Optional prior entry dict (for full prior hashes).
    """
    record = {
        'timestamp': _now_iso(),
        'operation': operation,
        'name': name,
    }

    if changes:
        record['changes'] = changes

    if prior_entry:
        record['prior_reasoning_hash'] = _hash_value(prior_entry.get('reasoning'))
        record['prior_body_hash'] = _hash_value(prior_entry.get('body'))

    os.makedirs(os.path.dirname(audit_path), exist_ok=True)

    with open(audit_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
