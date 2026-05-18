"""Tests for the web UI routes.

The UI modules capture config at import time, so the fixture rebinds the
constants on each consuming module (tree, kb, umap_cache) to point at a
sandboxed knowledge directory and ChromaDB.
"""

import os

import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    pytest.skip("fastapi extras not installed", allow_module_level=True)


@pytest.fixture
def kb_dir(tmp_dir):
    """A sandboxed knowledge directory with a few seed files."""
    root = os.path.join(tmp_dir, "knowledge")
    os.makedirs(os.path.join(root, "pipelines"))
    os.makedirs(os.path.join(root, "runbooks"))

    with open(os.path.join(root, "pipelines", "alpha.md"), "w") as f:
        f.write(
            "---\n"
            "title: Alpha\n"
            "description: Alpha pipeline overview\n"
            "category: pipelines\n"
            "---\n"
            "# Alpha\n\nPipeline that does alpha things.\n"
        )
    with open(os.path.join(root, "runbooks", "restart.md"), "w") as f:
        f.write(
            "---\n"
            "title: Restart\n"
            "description: How to restart the service\n"
            "category: runbooks\n"
            "---\n"
            "# Restart\n\nRun the restart script.\n"
        )
    return root


@pytest.fixture
def client(monkeypatch, kb_dir, chromadb_path):
    """A FastAPI TestClient with config pointed at sandboxed paths.

    Modules in knowledge_semantic.ui late-bind to `config.X` rather than
    importing the names directly, so patching the config module attributes
    propagates correctly to every consumer.
    """
    from knowledge_semantic.ui import config
    from knowledge_semantic.ui.services import kb

    monkeypatch.setattr(config, "KNOWLEDGE_PATH", kb_dir)
    monkeypatch.setattr(config, "CHROMADB_PATH", chromadb_path)
    monkeypatch.setattr(kb, "_store", None)

    # Seed: index the two files so map / status have content.
    kb.upsert_with_retry(
        os.path.join(kb_dir, "pipelines", "alpha.md"),
        open(os.path.join(kb_dir, "pipelines", "alpha.md")).read(),
    )
    kb.upsert_with_retry(
        os.path.join(kb_dir, "runbooks", "restart.md"),
        open(os.path.join(kb_dir, "runbooks", "restart.md")).read(),
    )

    from knowledge_semantic.ui.app import create_app

    return TestClient(create_app())


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_tree_returns_seed_files(client, kb_dir):
    r = client.get("/api/tree")
    assert r.status_code == 200
    root = r.json()["root"]
    assert root["isDir"] is True
    paths = _flatten_paths(root)
    assert os.path.join(kb_dir, "pipelines", "alpha.md") in paths
    assert os.path.join(kb_dir, "runbooks", "restart.md") in paths


def test_get_file_returns_content_and_frontmatter(client, kb_dir):
    path = os.path.join(kb_dir, "pipelines", "alpha.md")
    r = client.get("/api/file", params={"path": path})
    assert r.status_code == 200
    data = r.json()
    assert data["path"] == path
    assert "Alpha" in data["content"]
    assert data["frontmatter"]["description"] == "Alpha pipeline overview"
    assert data["frontmatter"]["category"] == "pipelines"
    assert "# Alpha" in data["body"]


def test_get_file_rejects_path_traversal(client):
    r = client.get("/api/file", params={"path": "/etc/passwd"})
    assert r.status_code == 400


def test_put_file_writes_and_indexes(client, kb_dir):
    path = os.path.join(kb_dir, "pipelines", "alpha.md")
    new_content = (
        "---\n"
        "title: Alpha\n"
        "description: Alpha pipeline overview\n"
        "category: pipelines\n"
        "---\n"
        "# Alpha\n\nUPDATED body content.\n"
    )
    r = client.put("/api/file", json={"path": path, "content": new_content})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "indexed"

    with open(path) as f:
        assert "UPDATED" in f.read()


def test_put_file_rejects_path_traversal(client):
    r = client.put(
        "/api/file",
        json={"path": "/etc/evil.md", "content": "x"},
    )
    assert r.status_code == 400


def test_put_file_rejects_non_markdown(client, kb_dir):
    r = client.put(
        "/api/file",
        json={"path": os.path.join(kb_dir, "evil.txt"), "content": "x"},
    )
    assert r.status_code == 400


def test_status_reports_indexed_count(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json()["total_indexed"] == 2


def _flatten_paths(node):
    out = [node["path"]] if not node.get("isDir") else []
    for c in node.get("children", []) or []:
        out.extend(_flatten_paths(c))
    return out
