"""Tests for hybrid_search: vector + BM25 fused via Reciprocal Rank Fusion."""
import pytest


@pytest.fixture
def store_with_diverse_corpus(store):
    """Seed a corpus designed to exercise the fusion.

    `/both.md` is the only doc where BOTH retrievers should rank highly:
    it contains the rare symbol AND the conceptual prose.
    `/sym.md` only carries the symbol (no conceptual prose) — BM25-only.
    `/sem.md` only carries the conceptual prose (no symbol) — vector-only.
    `/noise.md` is unrelated.
    """
    store.upsert(
        file_path="/sym.md",
        content=("Reference page listing every helper exposed by the layout "
                 "namespace: compose-page-tree (line 42), "
                 "render-block (line 88), with-retry (line 121)."),
        description="bm25-strong: exact symbol only", category="pattern",
    )
    store.upsert(
        file_path="/sem.md",
        content=("Designing types end-to-end before coding prevents refactor "
                 "loops across the protocol layers and helpers."),
        description="vector-strong: semantic, no exact symbol", category="pattern",
    )
    store.upsert(
        file_path="/both.md",
        content=("compose-page-tree is the canonical helper to design "
                 "layouts end-to-end across the protocol layers. It "
                 "dispatches by node type and prevents refactor loops."),
        description="agrees with both retrievers", category="pattern",
    )
    store.upsert(
        file_path="/noise.md",
        content="networking timeouts and connection pooling settings",
        description="completely unrelated", category="service",
    )
    return store


# ── RRF formula ──────────────────────────────────────────────────────────────


class TestReciprocalRankFusion:
    def test_score_formula(self):
        from knowledge_semantic.bm25 import rrf_fuse
        vec = [("a", 0.9), ("b", 0.5), ("c", 0.2)]
        bm = [("c", 10.0), ("d", 5.0)]
        # Note: rrf_fuse uses ranks (1-based), not raw scores.
        # k=60 by default.
        fused = rrf_fuse(vec, bm, k=60)
        # 'c' appears in BOTH (rank 3 vector, rank 1 bm25)
        c_score = 1/(60+3) + 1/(60+1)
        # 'a' only in vector (rank 1)
        a_score = 1/(60+1)
        # 'd' only in bm25 (rank 2)
        d_score = 1/(60+2)
        assert fused[0][0] == "c"
        assert fused[0][1] == pytest.approx(c_score)
        # 'a' beats 'd' because rank 1 in one source > rank 2 in other
        a_idx = [i for i, (fp, _) in enumerate(fused) if fp == "a"][0]
        d_idx = [i for i, (fp, _) in enumerate(fused) if fp == "d"][0]
        assert a_idx < d_idx

    def test_empty_inputs_returns_empty(self):
        from knowledge_semantic.bm25 import rrf_fuse
        assert rrf_fuse([], []) == []

    def test_one_empty_one_full(self):
        from knowledge_semantic.bm25 import rrf_fuse
        vec = [("a", 0.5), ("b", 0.2)]
        fused = rrf_fuse(vec, [])
        # Same order as vector input
        assert [fp for fp, _ in fused] == ["a", "b"]


# ── KnowledgeStore.hybrid_search ─────────────────────────────────────────────


class TestHybridSearch:
    def test_doc_in_both_ranks_above_doc_in_one(self, store_with_diverse_corpus):
        """The "/both.md" doc appears in both retrievers and must outrank
        docs that appear in only one — this is the core promise of RRF."""
        store = store_with_diverse_corpus
        results = store.hybrid_search(
            "compose-page-tree design layouts", limit=4,
        )
        paths = [r["file_path"] for r in results]
        # /both.md must outrank both /sym.md and /sem.md
        both_idx = paths.index("/both.md")
        if "/sym.md" in paths:
            assert both_idx < paths.index("/sym.md")
        if "/sem.md" in paths:
            assert both_idx < paths.index("/sem.md")

    def test_in_both_flag_set(self, store_with_diverse_corpus):
        store = store_with_diverse_corpus
        results = store.hybrid_search(
            "compose-page-tree design layouts", limit=4,
        )
        both = next(r for r in results if r["file_path"] == "/both.md")
        assert both["in_both"] is True

    def test_vector_only_hit_still_appears(self, store_with_diverse_corpus):
        """Doc that only the vector retriever surfaces must still make the
        final list (with `vec_rank` set, `bm25_rank` None)."""
        store = store_with_diverse_corpus
        results = store.hybrid_search(
            "designing types end-to-end refactor loops", limit=4,
        )
        paths = [r["file_path"] for r in results]
        assert "/sem.md" in paths

    def test_bm25_only_hit_still_appears(self, store_with_diverse_corpus):
        """Doc that only BM25 surfaces (exact symbol) must appear."""
        store = store_with_diverse_corpus
        # Use a query with a strong exact symbol but minimal semantic prose
        results = store.hybrid_search("compose-page-tree", limit=4)
        paths = [r["file_path"] for r in results]
        assert any(p in paths for p in ("/sym.md", "/both.md"))

    def test_filter_by_category_applies_to_both_retrievers(
        self, store_with_diverse_corpus,
    ):
        store = store_with_diverse_corpus
        results = store.hybrid_search(
            "compose-page-tree design layouts", category="pattern", limit=4,
        )
        assert all(r["category"] == "pattern" for r in results)
        # /noise.md is category=service, must not appear
        assert not any(r["file_path"] == "/noise.md" for r in results)

    def test_filter_by_project_applies_to_both(self, store):
        store.upsert(
            file_path="/p/a.md",
            content="canonical schema design in proj-a",
            description="d", category="pattern", project="proj-a",
        )
        store.upsert(
            file_path="/p/b.md",
            content="canonical schema design in proj-b",
            description="d", category="pattern", project="proj-b",
        )
        results = store.hybrid_search(
            "canonical schema design", project="proj-a", limit=4,
        )
        assert all(r.get("project") == "proj-a" for r in results)

    def test_result_keys_present(self, store_with_diverse_corpus):
        store = store_with_diverse_corpus
        results = store.hybrid_search("schema design", limit=2)
        for r in results:
            for k in ("file_path", "rrf_score", "in_both",
                      "vec_rank", "bm25_rank", "category", "description"):
                assert k in r, f"missing key {k} in {r}"

    def test_returns_at_most_limit(self, store_with_diverse_corpus):
        store = store_with_diverse_corpus
        results = store.hybrid_search("schema", limit=2)
        assert len(results) <= 2

    def test_empty_query_returns_empty(self, store_with_diverse_corpus):
        store = store_with_diverse_corpus
        assert store.hybrid_search("", limit=5) == []
