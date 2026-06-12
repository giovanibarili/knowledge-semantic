"""
conftest.py — Shared fixtures for knowledge-semantic tests.

Provides isolated ChromaDB instances so tests never touch real data.
"""

import os
import shutil
import tempfile

import pytest


@pytest.fixture
def tmp_dir():
    """Create and auto-cleanup a temporary directory."""
    d = tempfile.mkdtemp(prefix="ks_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def chromadb_path(tmp_dir):
    """Path to an empty ChromaDB directory inside tmp_dir."""
    p = os.path.join(tmp_dir, "chromadb")
    os.makedirs(p)
    return p


@pytest.fixture
def store(chromadb_path):
    """A KnowledgeStore pointing at the temp ChromaDB."""
    from knowledge_semantic.store import KnowledgeStore

    return KnowledgeStore(chromadb_path=chromadb_path)


@pytest.fixture
def seeded_store(store):
    """Store pre-loaded with sample documents using generic example terms."""
    store.upsert(
        file_path="/knowledge/services/auth.md",
        content="The auth service handles 5B requests per month with p99 of 60ms.",
        description="auth service overview",
        category="service",
        glossary_terms=[
            {
                "term": "AUTH",
                "aliases": ["auth-service"],
                "definition": "Authorization service",
            },
        ],
    )
    store.upsert(
        file_path="/knowledge/patterns/layered.md",
        content="Layered architecture defines tiers: controller, logic, adapter, wire.",
        description="Layered architecture tier structure",
        category="pattern",
        glossary_terms=[
            {
                "term": "Layered",
                "aliases": ["layered-architecture"],
                "definition": "Tier architecture pattern",
            },
        ],
    )
    store.upsert(
        file_path="/knowledge/domain/glossary/index.md",
        content="Glossary of domain terms: AUTH, UMS, PMS.",
        description="Domain glossary master index",
        category="domain",
        glossary_terms=[
            {
                "term": "UMS",
                "aliases": ["user-management-service"],
                "definition": "User lifecycle service",
            },
            {
                "term": "PMS",
                "aliases": ["payment-management-service"],
                "definition": "Payment processing service",
            },
        ],
    )
    return store
