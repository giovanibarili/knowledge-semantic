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

from .bm25 import BM25Store, rrf_fuse
from .frontmatter import extract_index_metadata, parse_frontmatter

logger = logging.getLogger("knowledge_semantic")

COLLECTION_NAME = "knowledge"

# OKF reserved filenames — directory listings / change history, not concepts.
# Skipped by reindex so they never enter the search corpus.
_RESERVED_FILES = {"index.md", "log.md"}


def _parse_glossary_terms(raw):
    """Parse glossary_terms from ChromaDB metadata.

    ChromaDB stores metadata values as strings, so glossary_terms is stored
    as a JSON-encoded string. However, in-memory test collections may store
    the value as a list directly. This helper handles both cases defensively.
    """
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        # Unwrap multiply-encoded JSON strings
        while isinstance(parsed, str):
            parsed = json.loads(parsed)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class KnowledgeStore:
    """Wrapper around ChromaDB for knowledge file storage and retrieval."""

    def __init__(self, chromadb_path=None):
        path = chromadb_path or os.environ.get(
            "CHROMADB_PATH",
            os.path.expanduser("~/dev/personal/claude-dotfiles/knowledge/.chromadb"),
        )
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)
        # Lazy BM25 — rebuilt on first hybrid_search() call and invalidated
        # on upsert/remove (mark-dirty pattern, keeps rebuilds amortised).
        self._bm25_store = BM25Store(self._collection)
        self._bm25_dirty = True

    def upsert(self, file_path, content, description, category, glossary_terms=None,
               project=None, domain=None, type=None):
        """Index or update a knowledge file in ChromaDB.

        `type` is the OKF artifact kind (open vocabulary, e.g. Pattern,
        Service, Runbook). It is stored as a filterable metadata field
        alongside `category` (the closed enum) and coexists with `domain`.
        """
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
        if domain:
            metadata["domain"] = domain
        if type:
            metadata["type"] = type

        self._collection.upsert(
            ids=[file_path],
            documents=[content],
            metadatas=[metadata],
        )
        # Corpus changed — invalidate BM25 index (next hybrid_search rebuilds)
        self._bm25_dirty = True

        return {
            "file_path": file_path,
            "terms_indexed": len(terms),
            "status": "updated" if is_update else "created",
            **({"domain": domain} if domain else {}),
        }

    def indexed_at(self, file_path):
        """Return the stored indexed_at timestamp (epoch seconds) for a file.

        Returns None if the file is not indexed or has no parseable timestamp.
        Lets external callers replicate the mtime-skip logic without reaching
        into the collection directly.
        """
        existing = self._collection.get(ids=[file_path])
        if not existing["ids"]:
            return None
        stamp = existing["metadatas"][0].get("indexed_at", "")
        try:
            return datetime.fromisoformat(stamp).timestamp() if stamp else None
        except ValueError:
            return None

    def search(self, query, category=None, project=None, domain=None, type=None, limit=5):
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
        if domain:
            where_clauses.append({"domain": domain})
        if type:
            where_clauses.append({"type": type})

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
                "type": meta.get("type", ""),
                "glossary_terms": _parse_glossary_terms(meta.get("glossary_terms", "[]")),
            }
            if meta.get("project"):
                hit["project"] = meta["project"]
            if meta.get("domain"):
                hit["domain"] = meta["domain"]
            hits.append(hit)

        return hits

    def hybrid_search(self, query, category=None, project=None, domain=None, type=None,
                      limit=5, k=60):
        """Hybrid retrieval = vector (semantic) + BM25 (lexical) fused via RRF.

        Vector and BM25 individually shine on different query shapes:
        - Vector finds paraphrases and conceptual matches (e.g. "how to handle
          authentication" → "auth flow rationale").
        - BM25 finds exact identifiers, acronyms, and kebab-case symbols
          (e.g. ":not-empty?", "JWT", "compose-page-tree") that embeddings
          collapse into the same neighbourhood.

        Reciprocal Rank Fusion merges them at the rank level, side-stepping
        the score-scale mismatch (cosine vs BM25). Each retriever contributes
        up to `RETRIEVER_K=20` candidates; the fused top-`limit` is returned.

        Each result is decorated with:
          - `rrf_score`     — the fused score (higher = better)
          - `vec_rank`      — rank in vector retriever (1-based) or None
          - `bm25_rank`     — rank in BM25 retriever (1-based) or None
          - `in_both`       — True if both retrievers surfaced this doc
          - `description`, `category`, `project`  — from ChromaDB metadata
        """
        if not query or not query.strip():
            return []

        # Each retriever returns its own ranked list; we fuse them.
        # Top-20 from each is the standard default in hybrid-search literature.
        RETRIEVER_K = 20

        vec_hits = self.search(
            query=query, category=category, project=project, domain=domain, type=type,
            limit=RETRIEVER_K,
        )

        if self._bm25_dirty:
            self._bm25_store.rebuild()
            self._bm25_dirty = False
        bm25_hits = self._bm25_store.search(
            query=query, category=category, project=project, domain=domain, type=type,
            limit=RETRIEVER_K,
        )

        vec_ranks = {h["file_path"]: i + 1 for i, h in enumerate(vec_hits)}
        bm25_ranks = {h["file_path"]: i + 1 for i, h in enumerate(bm25_hits)}

        # Build a metadata lookup so the fused output preserves description /
        # category / project from whichever retriever saw the doc.
        meta_by_path: dict[str, dict] = {}
        for h in vec_hits:
            meta_by_path.setdefault(h["file_path"], h)
        for h in bm25_hits:
            meta_by_path.setdefault(h["file_path"], h)

        # RRF — keep rrf_fuse pure (only ranks); we pair with metadata after.
        vec_ranking = [(h["file_path"], 0.0) for h in vec_hits]
        bm25_ranking = [(h["file_path"], 0.0) for h in bm25_hits]
        fused = rrf_fuse(vec_ranking, bm25_ranking, k=k)

        out = []
        for fp, score in fused[:limit]:
            meta = meta_by_path.get(fp, {})
            hit = {
                "file_path": fp,
                "rrf_score": round(score, 4),
                "vec_rank": vec_ranks.get(fp),
                "bm25_rank": bm25_ranks.get(fp),
                "in_both": fp in vec_ranks and fp in bm25_ranks,
                "description": meta.get("description", ""),
                "category": meta.get("category", ""),
                "type": meta.get("type", ""),
                "glossary_terms": _parse_glossary_terms(meta.get("glossary_terms", "[]")),
            }
            if meta.get("project"):
                hit["project"] = meta["project"]
            if meta.get("domain"):
                hit["domain"] = meta["domain"]
            out.append(hit)
        return out

    def glossary(self, term=None):
        """List or search glossary terms across all indexed files."""
        all_docs = self._collection.get(include=["metadatas"], limit=10000)

        terms = []
        for file_path, meta in zip(all_docs["ids"], all_docs["metadatas"]):
            stored_terms = _parse_glossary_terms(meta.get("glossary_terms", "[]"))
            for t in stored_terms:
                if not isinstance(t, dict):
                    continue
                entry = {
                    "term": t["term"],
                    "aliases": t.get("aliases", []),
                    "definition": t.get("definition", ""),
                    "source_file": file_path,
                }
                if meta.get("domain"):
                    entry["domain"] = meta["domain"]
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
        self._bm25_dirty = True
        return {"file_path": file_path, "status": "removed"}

    def reindex(self, directory, recursive=True, domain=None):
        """Walk a directory and index/update all .md files.

        Metadata (description, category, project, glossary_terms) is read from
        each file's YAML frontmatter via extract_index_metadata. Files without
        frontmatter fall back to description from the first prose line (the
        frontmatter block itself is skipped) and category "unknown". Files
        already indexed whose mtime is older than indexed_at are skipped.

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
                if fname in _RESERVED_FILES:
                    # OKF reserved (directory listing / change history) — not a
                    # concept document, so it never enters the search corpus.
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

                fm = extract_index_metadata(content) or {}
                _meta, body = parse_frontmatter(content)
                first_line = ""
                for line in body.splitlines():
                    stripped = line.strip().lstrip("#").strip()
                    if stripped:
                        first_line = stripped
                        break
                description = fm.get("description") or (first_line[:200] if first_line else fname)

                self.upsert(
                    file_path=abs_path,
                    content=content,
                    description=description,
                    category=fm.get("category", "unknown"),
                    glossary_terms=fm.get("glossary_terms", []),
                    project=fm.get("project"),
                    domain=domain,
                    type=fm.get("type"),
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
