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
    """Store pre-loaded with sample documents."""
    store.upsert(
        file_path="/knowledge/services/saa.md",
        content="Simple Account Authorizer handles 5B transactions per month with p99 of 60ms.",
        description="SAA authorization engine overview",
        category="service",
        glossary_terms=[
            {
                "term": "SAA",
                "aliases": ["simple-account-authorizer"],
                "definition": "Authorization engine",
            },
        ],
    )
    store.upsert(
        file_path="/knowledge/patterns/diplomat.md",
        content="Diplomat Architecture defines layers: controller, logic, diplomat, wire.",
        description="Diplomat Architecture layer structure",
        category="pattern",
        glossary_terms=[
            {
                "term": "Diplomat",
                "aliases": ["diplomat-architecture"],
                "definition": "Layer architecture pattern",
            },
        ],
    )
    store.upsert(
        file_path="/knowledge/domain/glossary/index.md",
        content="Glossary of domain terms: SAA, SAM, GDM, PTP, Diablo.",
        description="Domain glossary master index",
        category="domain",
        glossary_terms=[
            {
                "term": "SAM",
                "aliases": ["simple-account-manager"],
                "definition": "Account lifecycle manager",
            },
            {
                "term": "GDM",
                "aliases": ["global-deposits-manager"],
                "definition": "Yield and accrual manager",
            },
        ],
    )
    return store
