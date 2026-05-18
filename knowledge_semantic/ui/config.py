"""Configuration resolution for the web UI.

Mirrors the env vars documented in the project README:
- KNOWLEDGE_PATH (default: ~/knowledge)
- CHROMADB_PATH  (default: $KNOWLEDGE_PATH/.chromadb)
"""

import os


def _expand(path):
    return os.path.realpath(os.path.expanduser(path))


KNOWLEDGE_PATH = _expand(os.environ.get("KNOWLEDGE_PATH", "~/knowledge"))

CHROMADB_PATH = _expand(
    os.environ.get("CHROMADB_PATH", os.path.join(KNOWLEDGE_PATH, ".chromadb"))
)

HOST = os.environ.get("KB_UI_HOST", "127.0.0.1")
PORT = int(os.environ.get("KB_UI_PORT", "7878"))
