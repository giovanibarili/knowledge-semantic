"""Tests for the frontmatter parser module."""

from knowledge_semantic.frontmatter import extract_index_metadata, parse_frontmatter


class TestParseFrontmatter:
    def test_basic_frontmatter(self):
        content = """---
description: SAA authorization engine overview
category: service
---

# SAA

Content here.
"""
        meta, body = parse_frontmatter(content)
        assert meta is not None
        assert meta["description"] == "SAA authorization engine overview"
        assert meta["category"] == "service"
        assert "# SAA" in body

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
  - SAA
  - SAM
  - GDM
---

Body.
"""
        meta, body = parse_frontmatter(content)
        assert meta["glossary_terms"] == ["SAA", "SAM", "GDM"]

    def test_frontmatter_with_multiline_description(self):
        content = """---
description: >
  HOF+Registry pattern for multi-provider support.
  Rejected Protocol approach due to coupling.
category: decisions
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert "HOF+Registry" in meta["description"]
        assert "coupling" in meta["description"]

    def test_frontmatter_with_project(self):
        content = """---
description: Offer flow decisions
category: decisions
project: offer-manager
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert meta["project"] == "offer-manager"

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
glossary_terms: [SAA, SAM, GDM]
---

Body.
"""
        meta, _body = parse_frontmatter(content)
        assert meta["glossary_terms"] == ["SAA", "SAM", "GDM"]


class TestExtractIndexMetadata:
    def test_full_metadata(self):
        content = """---
description: SAA overview
category: service
project: offer-manager
glossary_terms:
  - SAA
  - SAM
---

Body.
"""
        result = extract_index_metadata(content)
        assert result["description"] == "SAA overview"
        assert result["category"] == "service"
        assert result["project"] == "offer-manager"
        assert len(result["glossary_terms"]) == 2
        assert result["glossary_terms"][0] == {"term": "SAA"}

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
  - term: SAA
    aliases: [simple-account-authorizer]
    definition: Authorization engine
  - term: SAM
    definition: Account manager
---

Body.
"""
        result = extract_index_metadata(content)
        assert len(result["glossary_terms"]) == 2
        assert result["glossary_terms"][0]["term"] == "SAA"
        assert result["glossary_terms"][0]["aliases"] == ["simple-account-authorizer"]
        assert result["glossary_terms"][1]["term"] == "SAM"
