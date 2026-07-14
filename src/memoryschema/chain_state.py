"""Active chain state management.

Tracks which chain entity is currently authorised (read-write).
All other memories are unauthorised (read-only) by default.

State is stored in memory/.active_chain (a single line: the chain name).
"""

import os


def get_active_chain(project_root=None):
    """Return the name of the active chain, or None if no chain is active."""
    if project_root is None:
        from memoryschema.config import MemoryConfig
        project_root = str(MemoryConfig().project_root or '.')
    path = os.path.join(project_root, 'memory', '.active_chain')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            name = f.read().strip()
        return name if name else None
    return None


def set_active_chain(name, project_root=None):
    """Set the active chain. Only one chain can be active at a time."""
    if project_root is None:
        from memoryschema.config import MemoryConfig
        project_root = str(MemoryConfig().project_root or '.')
    path = os.path.join(project_root, 'memory', '.active_chain')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(name + '\n')
    return name


def release_active_chain(project_root=None):
    """Release the active chain (make it read-only). Returns the released name."""
    if project_root is None:
        from memoryschema.config import MemoryConfig
        project_root = str(MemoryConfig().project_root or '.')
    path = os.path.join(project_root, 'memory', '.active_chain')
    released = None
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            released = f.read().strip()
        os.remove(path)
    return released if released else None
