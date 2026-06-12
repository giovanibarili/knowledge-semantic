"""
bm25.py — BM25 lexical retriever over the same corpus indexed in ChromaDB.

Complements the vector store with exact-token matching for Clojure symbols,
acronyms, and short technical queries where embeddings underperform.

The corpus is rebuilt from ChromaDB on demand (single source of truth — no
duplicated content store). For 100–1000 docs, rebuild is <300ms, so a lazy
strategy is good enough; for larger corpora introduce an `mark_dirty()` /
incremental rebuild path.

Tokenizer is Clojure-aware: it preserves kebab-case identifiers, predicate
suffix `?`, mutator suffix `!`, and namespace separator `/`. Pure punctuation
is dropped.
"""

import re
from typing import Any

from rank_bm25 import BM25Okapi


# Tokenizer regex. Matches contiguous runs of:
#   - word characters (letters, digits, _)
#   - the punctuation we treat as part of identifiers: - / . ? ! :
# Anything else is a delimiter. This keeps Clojure symbols intact while still
# splitting normal prose by whitespace + commas + parens etc.
#
# Examples:
#   "compose-page-tree"                   → ["compose-page-tree"]
#   ":not-empty?"                         → [":not-empty?"]
#   "validate-input!"                     → ["validate-input!"]
#   "my.namespace/some-fn"                → ["my.namespace/some-fn"]
#   "Hello, World."                       → ["hello", "world"]
_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-/.?!:]+")
# Tokens that are *only* punctuation are noise from the regex above (e.g. "."
# at end of a sentence). Strip them.
_PURE_PUNCT_RE = re.compile(r"^[\-/.?!:]+$")


def rrf_fuse(
    vec_ranking: list[tuple[str, float]],
    bm25_ranking: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: combine two rankings into one.

    For each document d appearing in ranking r at position rank_r(d) (1-based),
    contribute 1 / (k + rank_r(d)) to its fused score. Sum over all rankings
    in which d appears.

    Why RRF: the two retrievers produce scores on incompatible scales
    (vector cosine ∈ [-1, 1]; BM25 ∈ [0, ∞)). Normalising those scales
    introduces hyper-parameters per retriever. RRF sidesteps that by
    working with ranks only — it's robust, parameter-light, and a
    well-cited default for hybrid search (Cormack, Clarke, Büttcher, 2009).

    Default k=60 is the value originally proposed and used across most
    open-source hybrid search implementations (Elasticsearch, Vespa,
    Weaviate). Larger k softens the contribution of high-ranked items,
    smaller k sharpens it.

    Args:
        vec_ranking: list of (file_path, score) ordered by vector similarity.
                     Only the ORDER matters; scores are not used.
        bm25_ranking: list of (file_path, score) ordered by BM25 score.
        k: RRF constant (default 60).

    Returns:
        list of (file_path, rrf_score) sorted by rrf_score DESC.
    """
    fused: dict[str, float] = {}
    for rank, (fp, _) in enumerate(vec_ranking, start=1):
        fused[fp] = fused.get(fp, 0.0) + 1.0 / (k + rank)
    for rank, (fp, _) in enumerate(bm25_ranking, start=1):
        fused[fp] = fused.get(fp, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: -x[1])


def tokenize(text: str) -> list[str]:
    """Lower-case Clojure-aware tokenizer.

    Returns a list of lower-cased tokens, preserving identifier punctuation
    that carries meaning in Clojure (`-`, `/`, `?`, `!`, `:`, `.`).
    Pure-punctuation strings are dropped.
    """
    raw = _TOKEN_RE.findall(text or "")
    out: list[str] = []
    for t in raw:
        if _PURE_PUNCT_RE.match(t):
            continue
        # Trim trailing `.` that came from sentence ends (e.g. "schema." → "schema")
        # but only when the `.` is at the *end* and there's no other internal
        # `.` (which would be a namespace separator we want to keep).
        if t.endswith(".") and t.count(".") == 1:
            t = t[:-1]
        if not t:
            continue
        out.append(t.lower())
    return out


class BM25Store:
    """In-memory BM25 over a ChromaDB collection.

    Reads documents from the bound collection on `rebuild()` and stays in
    memory until next rebuild. Filtering by `category` / `project` is applied
    *after* BM25 scoring.

    Design note — token-overlap gating
    -----------------------------------
    `rank_bm25.BM25Okapi` can return a score of 0 even for documents that
    legitimately contain query terms, when the IDF component degenerates in
    small or homogeneous corpora (e.g. a term present in ≥50% of docs gets
    IDF≈0). Sorting by score-only would then make all matches indistinguishable
    from non-matches.

    To stay faithful to "BM25 = lexical relevance", we use a two-tier gate:
    1. Token-overlap filter — a document is a candidate only if it shares
       at least one token with the query (the very definition of a lexical
       match).
    2. BM25 ranking — among the candidates, BM25 score determines the order.

    Documents with zero overlap are excluded, even if BM25 assigned a
    spurious positive score (e.g. via BM25+ variants); documents with overlap
    but BM25=0 are still returned (preferred over the degenerate "no hits at
    all" outcome).
    """

    def __init__(self, collection: Any):
        self._coll = collection
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._metadata: dict[str, dict] = {}
        # Per-document token sets — kept for overlap gating (see class docstring)
        self._corpus_token_sets: list[set[str]] = []

    # ── lifecycle ───────────────────────────────────────────────────────────

    def rebuild(self) -> None:
        """Re-read all documents from the bound collection and recompute BM25.

        Cheap for collections under ~5000 docs; consider incremental refresh
        if the corpus grows beyond that.
        """
        result = self._coll.get(include=["documents", "metadatas"], limit=100000)
        ids = result.get("ids", []) or []
        docs = result.get("documents", []) or []
        metas = result.get("metadatas", []) or []

        # Defensive: if a row has no document body, skip it (rare, but avoids
        # `None` crashing the tokenizer).
        corpus_tokens: list[list[str]] = []
        kept_ids: list[str] = []
        kept_meta: dict[str, dict] = {}
        for i, doc, meta in zip(ids, docs, metas):
            if not isinstance(doc, str) or not doc.strip():
                continue
            corpus_tokens.append(tokenize(doc))
            kept_ids.append(i)
            kept_meta[i] = meta or {}

        self._ids = kept_ids
        self._metadata = kept_meta
        self._corpus_token_sets = [set(t) for t in corpus_tokens]
        # rank_bm25 raises on empty corpus — guard it
        self._bm25 = BM25Okapi(corpus_tokens) if corpus_tokens else None

    def search(self, query: str, category: str | None = None,
               project: str | None = None, limit: int = 20) -> list[dict]:
        """Return up to `limit` documents matching `query`, filtered by
        category/project. Documents with zero token overlap are dropped.

        Each hit is decorated with the BM25 score and the original ChromaDB
        metadata. See class docstring for the overlap-gating rationale.
        """
        if self._bm25 is None:
            self.rebuild()
        if self._bm25 is None:  # still None → empty corpus
            return []

        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        q_set = set(q_tokens)

        scores = self._bm25.get_scores(q_tokens)

        # Candidate set: docs that share at least one token with the query.
        candidates = [
            (self._ids[i], float(scores[i]))
            for i in range(len(self._ids))
            if q_set & self._corpus_token_sets[i]
        ]
        # Rank by BM25 score (stable sort preserves insertion order on ties)
        candidates.sort(key=lambda x: -x[1])

        out: list[dict] = []
        for fp, score in candidates:
            meta = self._metadata.get(fp, {})
            if category and meta.get("category") != category:
                continue
            if project and meta.get("project") != project:
                continue
            hit = {
                "file_path": fp,
                "bm25_score": round(score, 3),
                "description": meta.get("description", ""),
                "category": meta.get("category", ""),
            }
            if meta.get("project"):
                hit["project"] = meta["project"]
            out.append(hit)
            if len(out) >= limit:
                break
        return out
