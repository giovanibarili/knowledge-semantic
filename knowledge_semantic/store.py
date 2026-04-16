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

    def upsert(self, file_path, content, description, category, glossary_terms=None, project=None):
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
        if project:
            metadata["project"] = project

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

    def search(self, query, category=None, project=None, limit=5):
        """Semantic search across indexed knowledge files."""
        kwargs = {
            "query_texts": [query],
            "n_results": limit,
            "include": ["metadatas", "distances"],
        }
        where_clauses = []
        if category:
            where_clauses.append({"category": category})
        if project:
            where_clauses.append({"project": project})

        if len(where_clauses) == 1:
            kwargs["where"] = where_clauses[0]
        elif len(where_clauses) > 1:
            kwargs["where"] = {"$and": where_clauses}

        results = self._collection.query(**kwargs)

        if not results["ids"] or not results["ids"][0]:
            return []

        hits = []
        for file_path, meta, dist in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hit = {
                "file_path": file_path,
                "similarity_score": round(1 - dist, 3),
                "description": meta.get("description", ""),
                "category": meta.get("category", ""),
                "glossary_terms": json.loads(meta.get("glossary_terms", "[]")),
            }
            if meta.get("project"):
                hit["project"] = meta["project"]
            hits.append(hit)

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

    def reindex(self, directory, recursive=True):
        """Walk a directory and index/update all .md files.

        Files are indexed with minimal metadata (description from first line,
        category "unknown"). Files already indexed whose mtime is older than
        indexed_at are skipped.

        Returns counts of indexed, skipped, and errored files.
        """
        indexed = []
        skipped = []
        errors = []

        if not os.path.isdir(directory):
            return {"error": f"Not a directory: {directory}"}

        for root, _dirs, files in os.walk(directory):
            for fname in sorted(files):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(root, fname)
                abs_path = os.path.abspath(fpath)

                try:
                    file_mtime = os.path.getmtime(abs_path)
                except OSError:
                    errors.append({"file_path": abs_path, "reason": "cannot stat"})
                    continue

                existing = self._collection.get(ids=[abs_path])
                if existing["ids"]:
                    indexed_at_str = existing["metadatas"][0].get("indexed_at", "")
                    if indexed_at_str:
                        try:
                            indexed_at = datetime.fromisoformat(indexed_at_str).timestamp()
                            if file_mtime <= indexed_at:
                                skipped.append(abs_path)
                                continue
                        except ValueError:
                            pass

                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except OSError as e:
                    errors.append({"file_path": abs_path, "reason": str(e)})
                    continue

                first_line = ""
                for line in content.splitlines():
                    stripped = line.strip().lstrip("#").strip()
                    if stripped:
                        first_line = stripped
                        break
                description = first_line[:200] if first_line else fname

                self.upsert(
                    file_path=abs_path,
                    content=content,
                    description=description,
                    category="unknown",
                    glossary_terms=[],
                )
                indexed.append(abs_path)

            if not recursive:
                break

        return {
            "indexed": len(indexed),
            "skipped": len(skipped),
            "errors": len(errors),
            "indexed_files": indexed,
            "skipped_files": skipped,
            "error_details": errors,
        }

    def status(self):
        """Report index health: total files, stale files, orphaned entries.

        Stale = file on disk has mtime > indexed_at.
        Orphaned = file in index but no longer exists on disk.
        """
        all_docs = self._collection.get(include=["metadatas"], limit=10000)

        total = len(all_docs["ids"])
        stale = []
        orphaned = []
        last_indexed = None

        for file_path, meta in zip(all_docs["ids"], all_docs["metadatas"]):
            indexed_at_str = meta.get("indexed_at", "")

            if indexed_at_str:
                if last_indexed is None or indexed_at_str > last_indexed:
                    last_indexed = indexed_at_str

            if not os.path.isfile(file_path):
                orphaned.append(file_path)
                continue

            if indexed_at_str:
                try:
                    indexed_at = datetime.fromisoformat(indexed_at_str).timestamp()
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime > indexed_at:
                        stale.append(file_path)
                except (ValueError, OSError):
                    pass

        return {
            "total_indexed": total,
            "stale_count": len(stale),
            "stale_files": stale,
            "orphaned_count": len(orphaned),
            "orphaned_files": orphaned,
            "last_indexed": last_indexed,
        }
