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
            content="AUTH handles requests.",
            description="AUTH overview",
            category="service",
            glossary_terms=[
                {
                    "term": "AUTH",
                    "aliases": ["auth-service"],
                    "definition": "Authorization service",
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
        results = seeded_store.search("AUTH", limit=1)
        assert len(results) <= 1

    def test_search_returns_glossary_terms(self, seeded_store):
        results = seeded_store.search("authorization service")
        top = results[0]
        assert "glossary_terms" in top


class TestGlossary:
    def test_glossary_all_terms(self, seeded_store):
        terms = seeded_store.glossary()
        assert len(terms) >= 3

    def test_glossary_search_by_term(self, seeded_store):
        terms = seeded_store.glossary(term="AUTH")
        assert any(t["term"] == "AUTH" for t in terms)

    def test_glossary_search_by_alias(self, seeded_store):
        terms = seeded_store.glossary(term="auth-service")
        assert len(terms) >= 1

    def test_glossary_case_insensitive(self, seeded_store):
        terms = seeded_store.glossary(term="auth")
        assert any(t["term"] == "AUTH" for t in terms)


class TestRemove:
    def test_remove_existing(self, seeded_store):
        result = seeded_store.remove("/knowledge/services/auth.md")
        assert result["status"] == "removed"
        results = seeded_store.search("AUTH authorization")
        paths = [r["file_path"] for r in results]
        assert "/knowledge/services/auth.md" not in paths

    def test_remove_nonexistent(self, store):
        result = store.remove("/nonexistent.md")
        assert result["status"] == "not_found"


class TestReindex:
    def test_reindex_indexes_md_files(self, store, tmp_dir):
        import os

        os.makedirs(os.path.join(tmp_dir, "docs"))
        with open(os.path.join(tmp_dir, "docs", "alpha.md"), "w") as f:
            f.write("# Alpha\nContent about alpha patterns.")
        with open(os.path.join(tmp_dir, "docs", "beta.md"), "w") as f:
            f.write("# Beta\nContent about beta service.")
        # Non-md file should be ignored
        with open(os.path.join(tmp_dir, "docs", "notes.txt"), "w") as f:
            f.write("This is not markdown.")

        result = store.reindex(os.path.join(tmp_dir, "docs"))
        assert result["indexed"] == 2
        assert result["errors"] == 0

    def test_reindex_skips_up_to_date_files(self, store, tmp_dir):
        import os
        import time

        fpath = os.path.join(tmp_dir, "current.md")
        with open(fpath, "w") as f:
            f.write("# Current\nAlready indexed content.")

        # Index once
        store.reindex(tmp_dir)

        # Wait a moment so mtime comparison is stable
        time.sleep(0.1)

        # Reindex again without modifying file
        result = store.reindex(tmp_dir)
        assert result["skipped"] == 1
        assert result["indexed"] == 0

    def test_reindex_updates_modified_files(self, store, tmp_dir):
        import os
        import time

        fpath = os.path.join(tmp_dir, "changing.md")
        with open(fpath, "w") as f:
            f.write("# Original\nOriginal content.")

        store.reindex(tmp_dir)
        time.sleep(0.1)

        # Modify the file
        with open(fpath, "w") as f:
            f.write("# Updated\nUpdated content.")

        result = store.reindex(tmp_dir)
        assert result["indexed"] == 1
        assert result["skipped"] == 0

    def test_reindex_recursive(self, store, tmp_dir):
        import os

        os.makedirs(os.path.join(tmp_dir, "a", "b"))
        with open(os.path.join(tmp_dir, "a", "top.md"), "w") as f:
            f.write("# Top\nTop level.")
        with open(os.path.join(tmp_dir, "a", "b", "nested.md"), "w") as f:
            f.write("# Nested\nNested content.")

        result = store.reindex(os.path.join(tmp_dir, "a"), recursive=True)
        assert result["indexed"] == 2

    def test_reindex_non_recursive(self, store, tmp_dir):
        import os

        os.makedirs(os.path.join(tmp_dir, "flat", "sub"))
        with open(os.path.join(tmp_dir, "flat", "here.md"), "w") as f:
            f.write("# Here\nTop level only.")
        with open(os.path.join(tmp_dir, "flat", "sub", "deep.md"), "w") as f:
            f.write("# Deep\nShould be skipped.")

        result = store.reindex(os.path.join(tmp_dir, "flat"), recursive=False)
        assert result["indexed"] == 1

    def test_reindex_not_a_directory(self, store):
        result = store.reindex("/nonexistent/path")
        assert "error" in result

    def test_reindex_uses_first_heading_as_description(self, store, tmp_dir):
        import os

        fpath = os.path.join(tmp_dir, "headed.md")
        with open(fpath, "w") as f:
            f.write("# My Great Title\nBody content here.")

        store.reindex(tmp_dir)
        results = store.search("My Great Title")
        assert any("My Great Title" in r["description"] for r in results)


class TestStatus:
    def test_status_empty_index(self, store):
        result = store.status()
        assert result["total_indexed"] == 0
        assert result["stale_count"] == 0
        assert result["orphaned_count"] == 0
        assert result["last_indexed"] is None

    def test_status_with_indexed_files(self, seeded_store):
        result = seeded_store.status()
        assert result["total_indexed"] == 3
        assert result["last_indexed"] is not None

    def test_status_detects_orphaned(self, store):
        # Index a file that does not exist on disk
        store.upsert(
            file_path="/nonexistent/ghost.md",
            content="Ghost content.",
            description="Ghost file",
            category="service",
        )
        result = store.status()
        assert result["orphaned_count"] == 1
        assert "/nonexistent/ghost.md" in result["orphaned_files"]

    def test_status_detects_stale(self, store, tmp_dir):
        import os
        import time

        fpath = os.path.join(tmp_dir, "stale.md")
        with open(fpath, "w") as f:
            f.write("# Original\nOriginal.")

        abs_path = os.path.abspath(fpath)
        store.upsert(
            file_path=abs_path,
            content="# Original\nOriginal.",
            description="Original",
            category="service",
        )

        time.sleep(0.1)

        # Modify file outside the store (simulates git pull / editor)
        with open(fpath, "w") as f:
            f.write("# Modified\nModified outside store.")

        result = store.status()
        assert result["stale_count"] == 1
        assert abs_path in result["stale_files"]


class TestProjectScoping:
    def test_upsert_with_project(self, store):
        result = store.upsert(
            file_path="/knowledge/orders.md",
            content="Orders service handles order lifecycle.",
            description="Orders service overview",
            category="service",
            project="orders-svc",
        )
        assert result["status"] == "created"

    def test_search_filter_by_project(self, store):
        store.upsert(
            file_path="/knowledge/orders.md",
            content="Orders service handles order lifecycle.",
            description="Orders service overview",
            category="service",
            project="orders-svc",
        )
        store.upsert(
            file_path="/knowledge/billing.md",
            content="Billing service handles payment processing.",
            description="Billing payment processing",
            category="service",
            project="billing-svc",
        )

        results = store.search("service overview", project="orders-svc")
        paths = [r["file_path"] for r in results]
        assert "/knowledge/orders.md" in paths
        assert "/knowledge/billing.md" not in paths

    def test_search_without_project_returns_all(self, store):
        store.upsert(
            file_path="/knowledge/a.md",
            content="Project A content about microservices.",
            description="Project A",
            category="service",
            project="project-a",
        )
        store.upsert(
            file_path="/knowledge/b.md",
            content="Project B content about microservices.",
            description="Project B",
            category="service",
            project="project-b",
        )

        results = store.search("microservices")
        assert len(results) == 2

    def test_search_filter_category_and_project(self, store):
        store.upsert(
            file_path="/knowledge/pattern.md",
            content="Layered architecture pattern.",
            description="Layered pattern",
            category="pattern",
            project="orders-svc",
        )
        store.upsert(
            file_path="/knowledge/svc.md",
            content="Orders service details.",
            description="Orders service",
            category="service",
            project="orders-svc",
        )

        results = store.search("orders", category="pattern", project="orders-svc")
        assert all(r["category"] == "pattern" for r in results)

    def test_search_result_includes_project(self, store):
        store.upsert(
            file_path="/knowledge/tagged.md",
            content="Tagged content.",
            description="Tagged file",
            category="service",
            project="my-project",
        )
        results = store.search("tagged content")
        assert results[0]["project"] == "my-project"

    def test_search_result_omits_project_when_none(self, store):
        store.upsert(
            file_path="/knowledge/global.md",
            content="Global knowledge file.",
            description="Global file",
            category="convention",
        )
        results = store.search("global knowledge")
        assert "project" not in results[0]


class TestOkfTypeDimension:
    """The OKF `type` dimension coexists with category/project/domain."""

    def test_upsert_and_filter_by_type(self, store):
        store.upsert(
            file_path="/knowledge/pat.md",
            content="A reusable design pattern about retries.",
            description="Retry pattern",
            category="pattern",
            type="Pattern",
        )
        store.upsert(
            file_path="/knowledge/svc.md",
            content="A service about retries and backoff.",
            description="Retry service",
            category="service",
            type="Service",
        )

        results = store.search("retries", type="Pattern")
        paths = [r["file_path"] for r in results]
        assert "/knowledge/pat.md" in paths
        assert "/knowledge/svc.md" not in paths

    def test_search_result_includes_type(self, store):
        store.upsert(
            file_path="/knowledge/typed.md",
            content="Typed content.",
            description="Typed file",
            category="service",
            type="Runbook",
        )
        results = store.search("typed content")
        assert results[0]["type"] == "Runbook"

    def test_reindex_skips_reserved_files(self, store, tmp_dir):
        import os

        with open(os.path.join(tmp_dir, "concept.md"), "w") as f:
            f.write("# Concept\nA real concept document.")
        # OKF reserved — directory listing / change history, not concepts
        with open(os.path.join(tmp_dir, "index.md"), "w") as f:
            f.write("# Index\nDirectory listing.")
        with open(os.path.join(tmp_dir, "log.md"), "w") as f:
            f.write("# Log\nChange history.")

        result = store.reindex(tmp_dir)
        assert result["indexed"] == 1

    def test_reindex_reads_type_from_frontmatter(self, store, tmp_dir):
        import os

        fpath = os.path.join(tmp_dir, "fm-typed.md")
        with open(fpath, "w") as f:
            f.write("---\ndescription: A runbook\ncategory: operations\ntype: Runbook\n---\n\n# Runbook\nSteps.")

        store.reindex(tmp_dir)
        results = store.search("runbook steps", type="Runbook")
        assert any(r["file_path"].endswith("fm-typed.md") for r in results)
