"""Tests for the ChromaDB store module."""


class TestUpsert:
    def test_upsert_creates_document(self, store):
        result = store.upsert(
            file_path="/knowledge/test.md",
            content="Test content about authentication.",
            description="Test file",
            category="service",
            glossary_terms=[],
        )
        assert result["status"] == "created"
        assert result["file_path"] == "/knowledge/test.md"
        assert result["terms_indexed"] == 0

    def test_upsert_updates_existing(self, store):
        store.upsert(
            file_path="/knowledge/test.md",
            content="Original content.",
            description="Original",
            category="service",
            glossary_terms=[],
        )
        result = store.upsert(
            file_path="/knowledge/test.md",
            content="Updated content.",
            description="Updated",
            category="service",
            glossary_terms=[],
        )
        assert result["status"] == "updated"

    def test_upsert_with_glossary_terms(self, store):
        result = store.upsert(
            file_path="/knowledge/test.md",
            content="SAA handles transactions.",
            description="SAA overview",
            category="service",
            glossary_terms=[
                {
                    "term": "SAA",
                    "aliases": ["simple-account-authorizer"],
                    "definition": "Auth engine",
                },
            ],
        )
        assert result["terms_indexed"] == 1


class TestSearch:
    def test_search_basic(self, seeded_store):
        results = seeded_store.search("account authorization")
        assert len(results) > 0
        assert "file_path" in results[0]
        assert "similarity_score" in results[0]
        assert "description" in results[0]

    def test_search_with_category_filter(self, seeded_store):
        results = seeded_store.search("architecture layers", category="pattern")
        assert all(r["category"] == "pattern" for r in results)

    def test_search_with_limit(self, seeded_store):
        results = seeded_store.search("SAA", limit=1)
        assert len(results) <= 1

    def test_search_returns_glossary_terms(self, seeded_store):
        results = seeded_store.search("authorization engine")
        top = results[0]
        assert "glossary_terms" in top


class TestGlossary:
    def test_glossary_all_terms(self, seeded_store):
        terms = seeded_store.glossary()
        assert len(terms) >= 3

    def test_glossary_search_by_term(self, seeded_store):
        terms = seeded_store.glossary(term="SAA")
        assert any(t["term"] == "SAA" for t in terms)

    def test_glossary_search_by_alias(self, seeded_store):
        terms = seeded_store.glossary(term="simple-account")
        assert len(terms) >= 1

    def test_glossary_case_insensitive(self, seeded_store):
        terms = seeded_store.glossary(term="saa")
        assert any(t["term"] == "SAA" for t in terms)


class TestRemove:
    def test_remove_existing(self, seeded_store):
        result = seeded_store.remove("/knowledge/services/saa.md")
        assert result["status"] == "removed"
        results = seeded_store.search("SAA authorization")
        paths = [r["file_path"] for r in results]
        assert "/knowledge/services/saa.md" not in paths

    def test_remove_nonexistent(self, store):
        result = store.remove("/nonexistent.md")
        assert result["status"] == "not_found"
