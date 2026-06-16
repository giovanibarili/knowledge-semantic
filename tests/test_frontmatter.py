"""Tests for the frontmatter parser module."""

from knowledge_semantic.frontmatter import extract_index_metadata, parse_frontmatter


class TestParseFrontmatter:
    def test_basic_frontmatter(self):
        content = """---
description: AUTH service overview
category: service
---

# AUTH

Content here.
"""
        meta, body = parse_frontmatter(content)
        assert meta is not None
        assert meta["description"] == "AUTH service overview"
        assert meta["category"] == "service"
        assert "# AUTH" in body

    def test_no_frontmatter(self):
        content = "# Just a heading\n\nNo frontmatter here."
        meta, body = parse_frontmatter(content)
        assert meta is None
        assert body == content

    def test_frontmatter_with_list(self):
        content = """---
description: Domain glossary
category: domain
glossary_terms:
  - AUTH
  - UMS
  - PMS
---

Body.
"""
        meta, body = parse_frontmatter(content)
        assert meta["glossary_terms"] == ["AUTH", "UMS", "PMS"]

    def test_frontmatter_with_multiline_description(self):
        content = """---
description: >
  Strategy pattern for multi-backend support.
  Rejected inheritance approach due to coupling.
category: decisions
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert "Strategy pattern" in meta["description"]
        assert "coupling" in meta["description"]

    def test_frontmatter_with_project(self):
        content = """---
description: Order flow decisions
category: decisions
project: demo-service
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert meta["project"] == "demo-service"

    def test_frontmatter_with_null_values(self):
        content = """---
description: Test file
category: service
project: null
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert meta["project"] is None

    def test_frontmatter_with_quoted_values(self):
        content = """---
description: "A quoted description"
category: 'service'
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert meta["description"] == "A quoted description"
        assert meta["category"] == "service"

    def test_frontmatter_with_inline_list(self):
        content = """---
description: Test
category: service
glossary_terms: [AUTH, UMS, PMS]
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert meta["glossary_terms"] == ["AUTH", "UMS", "PMS"]


class TestExtractIndexMetadata:
    def test_full_metadata(self):
        content = """---
description: AUTH overview
category: service
project: demo-service
glossary_terms:
  - AUTH
  - UMS
---

Body.
"""
        result = extract_index_metadata(content)
        assert result["description"] == "AUTH overview"
        assert result["category"] == "service"
        assert result["project"] == "demo-service"
        assert len(result["glossary_terms"]) == 2
        assert result["glossary_terms"][0] == {"term": "AUTH"}

    def test_partial_metadata(self):
        content = """---
description: Just a description
---

Body.
"""
        result = extract_index_metadata(content)
        assert result["description"] == "Just a description"
        assert "category" not in result

    def test_no_frontmatter_returns_none(self):
        content = "# No frontmatter\n\nJust content."
        result = extract_index_metadata(content)
        assert result is None

    def test_empty_frontmatter_returns_none(self):
        content = """---
---

Body.
"""
        result = extract_index_metadata(content)
        assert result is None

    def test_glossary_terms_as_dicts(self):
        content = """---
description: Glossary file
category: domain
glossary_terms:
  - term: AUTH
    aliases: [auth-service]
    definition: Authorization service
  - term: UMS
    definition: User management
---

Body.
"""
        result = extract_index_metadata(content)
        assert len(result["glossary_terms"]) == 2
        assert result["glossary_terms"][0]["term"] == "AUTH"
        assert result["glossary_terms"][0]["aliases"] == ["auth-service"]
        assert result["glossary_terms"][1]["term"] == "UMS"
