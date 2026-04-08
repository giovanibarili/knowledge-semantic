"""
store.py — ChromaDB storage layer for knowledge files.

Handles all ChromaDB interactions: upsert, search, glossary, remove.
The MCP server calls this module — it never touches ChromaDB directly.
"""

import json
import logging
import os
from datetime import datetime

import chromadb

logger = logging.getLogger("knowledge_semantic")

COLLECTION_NAME = "knowledge"


class KnowledgeStore:
    """Wrapper around ChromaDB for knowledge file storage and retrieval."""

    def __init__(self, chromadb_path=None):
        path = chromadb_path or os.environ.get(
            "CHROMADB_PATH",
            os.path.expanduser("~/dev/personal/claude-dotfiles/knowledge/.chromadb"),
        )
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    def upsert(self, file_path, content, description, category, glossary_terms=None):
        """Index or update a knowledge file in ChromaDB."""
        terms = glossary_terms or []
        existing = self._collection.get(ids=[file_path])
        is_update = len(existing["ids"]) > 0

        metadata = {
            "description": description,
            "category": category,
            "glossary_terms": json.dumps(terms),
            "indexed_at": datetime.now().isoformat(),
        }

        self._collection.upsert(
            ids=[file_path],
            documents=[content],
            metadatas=[metadata],
        )

        return {
            "file_path": file_path,
            "terms_indexed": len(terms),
            "status": "updated" if is_update else "created",
        }

    def search(self, query, category=None, limit=5):
        """Semantic search across indexed knowledge files."""
        kwargs = {
            "query_texts": [query],
            "n_results": limit,
            "include": ["metadatas", "distances"],
        }
        if category:
            kwargs["where"] = {"category": category}

        results = self._collection.query(**kwargs)

        if not results["ids"] or not results["ids"][0]:
            return []

        hits = []
        for file_path, meta, dist in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "file_path": file_path,
                    "similarity_score": round(1 - dist, 3),
                    "description": meta.get("description", ""),
                    "category": meta.get("category", ""),
                    "glossary_terms": json.loads(meta.get("glossary_terms", "[]")),
                }
            )

        return hits

    def glossary(self, term=None):
        """List or search glossary terms across all indexed files."""
        all_docs = self._collection.get(include=["metadatas"], limit=10000)

        terms = []
        for file_path, meta in zip(all_docs["ids"], all_docs["metadatas"]):
            raw = meta.get("glossary_terms", "[]")
            try:
                stored_terms = json.loads(raw)
                # Unwrap multiply-encoded JSON strings
                while isinstance(stored_terms, str):
                    stored_terms = json.loads(stored_terms)
            except (json.JSONDecodeError, TypeError):
                continue
            for t in stored_terms:
                if not isinstance(t, dict):
                    continue
                entry = {
                    "term": t["term"],
                    "aliases": t.get("aliases", []),
                    "definition": t.get("definition", ""),
                    "source_file": file_path,
                }
                if term:
                    search_lower = term.lower()
                    if search_lower in t["term"].lower() or any(
                        search_lower in a.lower() for a in t.get("aliases", [])
                    ):
                        terms.append(entry)
                else:
                    terms.append(entry)

        return terms

    def remove(self, file_path):
        """Remove a file from the index."""
        existing = self._collection.get(ids=[file_path])
        if not existing["ids"]:
            return {"file_path": file_path, "status": "not_found"}

        self._collection.delete(ids=[file_path])
        return {"file_path": file_path, "status": "removed"}
