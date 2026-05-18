"""Filesystem tree walker for the UI's file panel.

Returns a nested structure of directories and markdown files under
KNOWLEDGE_PATH. Hidden files and dot-directories are skipped.
"""

import os

from knowledge_semantic.ui import config


def _node(abs_path, is_dir, children=None):
    rel = os.path.relpath(abs_path, config.KNOWLEDGE_PATH)
    name = os.path.basename(abs_path) or rel
    category = rel.split(os.sep)[0] if os.sep in rel else (rel if is_dir else None)
    out = {
        "path": abs_path,
        "name": name,
        "isDir": is_dir,
        "category": category,
    }
    if is_dir:
        out["children"] = children or []
    return out


def build_tree(root=None):
    root = root or config.KNOWLEDGE_PATH
    if not os.path.isdir(root):
        return _node(root, True, [])
    return _walk(root)


def _walk(path):
    children = []
    try:
        entries = sorted(os.listdir(path))
    except OSError:
        return _node(path, True, [])

    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            children.append(_walk(full))
        elif entry.endswith(".md"):
            children.append(_node(full, False))
    return _node(path, True, children)


def is_inside_knowledge(path):
    """True if `path` resolves to a location under KNOWLEDGE_PATH.

    Both sides are normalized through realpath so the comparison survives
    symlink-laden temp dirs (e.g., macOS resolves /var/folders to /private/var).
    """
    try:
        real = os.path.realpath(path)
        real_root = os.path.realpath(config.KNOWLEDGE_PATH)
    except OSError:
        return False
    return real == real_root or real.startswith(real_root.rstrip(os.sep) + os.sep)
