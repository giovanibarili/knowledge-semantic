"""Singleton KnowledgeStore + safe write wrapper used by the UI routes."""

import time

from knowledge_semantic.frontmatter import extract_index_metadata, parse_frontmatter
from knowledge_semantic.store import KnowledgeStore
from knowledge_semantic.ui import config

_store = None


def get_store():
    global _store
    if _store is None:
        _store = KnowledgeStore(chromadb_path=config.CHROMADB_PATH)
    return _store


def warmup():
    """Eagerly load sentence-transformers so the first request isn't slow."""
    get_store().search("warmup", limit=1)


def parse(content):
    """Return (metadata_dict_or_None, body) for a markdown string."""
    return parse_frontmatter(content)


def upsert_with_retry(file_path, content, attempts=3, backoff_s=0.05):
    """Upsert a file into ChromaDB, retrying on transient SQLite locks.

    Returns the store's upsert result dict, plus a derived `description` and
    `category` so the route can return them without re-parsing.
    """
    meta = extract_index_metadata(content) or {}
    description = meta.get("description", "")
    category = meta.get("category", "uncategorized")
    glossary_terms = meta.get("glossary_terms", [])
    project = meta.get("project")

    last_err = None
    for attempt in range(attempts):
        try:
            result = get_store().upsert(
                file_path=file_path,
                content=content,
                description=description,
                category=category,
                glossary_terms=glossary_terms,
                project=project,
            )
            return {
                **result,
                "description": description,
                "category": category,
            }
        except Exception as e:
            last_err = e
            if "locked" in str(e).lower() and attempt < attempts - 1:
                time.sleep(backoff_s * (attempt + 1))
                continue
            raise

    raise last_err
