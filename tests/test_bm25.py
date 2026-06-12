"""Tests for the BM25 lexical retriever and its Clojure-aware tokenizer."""
import pytest


# ── tokenizer ────────────────────────────────────────────────────────────────


class TestTokenize:
    def test_lowercases_words(self):
        from knowledge_semantic.bm25 import tokenize
        assert tokenize("Hello World") == ["hello", "world"]

    def test_preserves_kebab_case_as_single_token(self):
        """Kebab-case symbols (e.g. `compose-page-tree`) are conceptually
        one identifier; the tokenizer keeps `-` joined."""
        from knowledge_semantic.bm25 import tokenize
        tokens = tokenize("compose-page-tree")
        assert "compose-page-tree" in tokens
        # Sub-tokens are NOT also emitted (avoid double-counting)
        assert "compose" not in tokens
        assert "page" not in tokens

    def test_preserves_predicate_question_mark(self):
        """Predicates ending with `?` (e.g. `:not-empty?`) — must stay attached."""
        from knowledge_semantic.bm25 import tokenize
        tokens = tokenize(":not-empty?")
        assert ":not-empty?" in tokens

    def test_preserves_bang_mutator(self):
        """Mutating functions end with `!` (e.g. `validate-input!`)."""
        from knowledge_semantic.bm25 import tokenize
        tokens = tokenize("validate-input!")
        assert "validate-input!" in tokens

    def test_preserves_namespace_slash(self):
        """`my.namespace/some-fn` is one symbol, not two."""
        from knowledge_semantic.bm25 import tokenize
        tokens = tokenize("my.namespace/some-fn")
        # We keep the whole symbol; lowercase it.
        assert "my.namespace/some-fn" in tokens

    def test_acronyms_preserved(self):
        from knowledge_semantic.bm25 import tokenize
        tokens = tokenize("JWT auth flow, OAuth and SAML supported")
        for t in ("jwt", "oauth", "saml"):
            assert t in tokens

    def test_drops_pure_punctuation(self):
        from knowledge_semantic.bm25 import tokenize
        # commas, periods (not in symbol) should not become tokens
        tokens = tokenize("hello, world.")
        assert "," not in tokens
        assert "." not in tokens


# ── BM25Store ────────────────────────────────────────────────────────────────


class TestBM25Store:
    def test_rebuilds_from_collection(self, seeded_store):
        from knowledge_semantic.bm25 import BM25Store
        bm = BM25Store(seeded_store._collection)
        bm.rebuild()
        # Sanity: we have docs indexed
        assert len(bm._ids) == 3

    def test_search_returns_exact_symbol_hit_first(self, store):
        """Query with a kebab-case symbol must rank the doc containing it #1."""
        from knowledge_semantic.bm25 import BM25Store

        store.upsert(
            file_path="/k/a.md", content="general overview of authorization",
            description="auth overview", category="service",
        )
        store.upsert(
            file_path="/k/b.md",
            content="The helper compose-page-tree assembles nested layouts.",
            description="layout composition", category="pattern",
        )
        store.upsert(
            file_path="/k/c.md", content="totally unrelated content about networking",
            description="net", category="service",
        )

        bm = BM25Store(store._collection)
        hits = bm.search("compose-page-tree", limit=5)
        assert hits, "BM25 must return at least one hit for the exact symbol"
        assert hits[0]["file_path"] == "/k/b.md"

    def test_search_ranks_acronym_match(self, store):
        store.upsert(
            file_path="/k/a.md", content="discussion of JWT token issuance",
            description="JWT auth", category="domain",
        )
        store.upsert(
            file_path="/k/b.md", content="generic message about identifiers",
            description="generic", category="domain",
        )

        from knowledge_semantic.bm25 import BM25Store
        bm = BM25Store(store._collection)
        hits = bm.search("JWT", limit=5)
        assert hits and hits[0]["file_path"] == "/k/a.md"

    def test_search_zero_score_excluded(self, store):
        """Docs that share no tokens with the query must NOT appear in results."""
        store.upsert(
            file_path="/k/a.md", content="quantum entanglement basics",
            description="physics", category="domain",
        )
        from knowledge_semantic.bm25 import BM25Store
        bm = BM25Store(store._collection)
        hits = bm.search("compose-page-tree namespace handler", limit=5)
        # No overlap → no hit
        assert hits == []

    def test_filter_by_category(self, store):
        store.upsert(
            file_path="/k/a.md", content="schema definition for Money",
            description="d", category="pattern",
        )
        store.upsert(
            file_path="/k/b.md", content="schema definition for Money",
            description="d", category="service",
        )
        from knowledge_semantic.bm25 import BM25Store
        bm = BM25Store(store._collection)
        hits = bm.search("schema Money", category="pattern", limit=5)
        assert all(h["category"] == "pattern" for h in hits)
        assert any(h["file_path"] == "/k/a.md" for h in hits)
        assert not any(h["file_path"] == "/k/b.md" for h in hits)

    def test_filter_by_project(self, store):
        store.upsert(
            file_path="/k/a.md", content="hello schema",
            description="d", category="pattern", project="proj-a",
        )
        store.upsert(
            file_path="/k/b.md", content="hello schema",
            description="d", category="pattern", project="proj-b",
        )
        from knowledge_semantic.bm25 import BM25Store
        bm = BM25Store(store._collection)
        hits = bm.search("schema", project="proj-a", limit=5)
        assert all(h.get("project") == "proj-a" for h in hits)

    def test_rebuild_picks_up_new_documents(self, store):
        from knowledge_semantic.bm25 import BM25Store
        store.upsert(
            file_path="/k/a.md", content="first doc about widgets",
            description="d", category="service",
        )
        bm = BM25Store(store._collection)
        bm.rebuild()
        assert len(bm._ids) == 1

        store.upsert(
            file_path="/k/b.md", content="second doc about gadgets",
            description="d", category="service",
        )
        bm.rebuild()
        assert len(bm._ids) == 2
