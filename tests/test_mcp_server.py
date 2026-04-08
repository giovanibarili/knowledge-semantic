"""Tests for the MCP server dispatch and tool handlers."""

import json
import os


def _patch_server(monkeypatch, store):
    """Patch the mcp_server module to use a test store."""
    from knowledge_semantic import mcp_server

    monkeypatch.setattr(mcp_server, "_store", store)


class TestProtocol:
    def test_initialize(self):
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request({"method": "initialize", "id": 1, "params": {}})
        assert resp["result"]["serverInfo"]["name"] == "knowledge-semantic"
        assert resp["id"] == 1

    def test_notifications_initialized_returns_none(self):
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request({"method": "notifications/initialized", "id": None, "params": {}})
        assert resp is None

    def test_tools_list(self):
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request({"method": "tools/list", "id": 2, "params": {}})
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools}
        assert names == {
            "knowledge_index",
            "knowledge_write",
            "knowledge_edit",
            "knowledge_search",
            "knowledge_glossary",
            "knowledge_remove",
        }

    def test_unknown_tool(self):
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 3,
                "params": {"name": "nonexistent", "arguments": {}},
            }
        )
        assert resp["error"]["code"] == -32601

    def test_unknown_method(self):
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request({"method": "unknown/method", "id": 4, "params": {}})
        assert resp["error"]["code"] == -32601


class TestKnowledgeIndex:
    def test_index_file(self, monkeypatch, store, tmp_dir):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        test_file = os.path.join(tmp_dir, "test.md")
        with open(test_file, "w") as f:
            f.write("# Test\nThis is about SAA authorization.")

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 10,
                "params": {
                    "name": "knowledge_index",
                    "arguments": {
                        "file_path": test_file,
                        "description": "Test file about SAA",
                        "category": "service",
                        "glossary_terms": [
                            {
                                "term": "SAA",
                                "aliases": ["simple-account-authorizer"],
                                "definition": "Auth engine",
                            },
                        ],
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "created"
        assert content["terms_indexed"] == 1

    def test_index_file_not_found(self, monkeypatch, store):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 11,
                "params": {
                    "name": "knowledge_index",
                    "arguments": {
                        "file_path": "/nonexistent/file.md",
                        "description": "Does not exist",
                        "category": "service",
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content


class TestKnowledgeWrite:
    def test_write_creates_file_and_indexes(self, monkeypatch, store, tmp_dir):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        test_file = os.path.join(tmp_dir, "subdir", "new.md")
        resp = handle_request(
            {
                "method": "tools/call",
                "id": 50,
                "params": {
                    "name": "knowledge_write",
                    "arguments": {
                        "file_path": test_file,
                        "content": "# New File\nContent about Datomic patterns.",
                        "description": "New knowledge file about Datomic",
                        "category": "pattern",
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "created"

        # Verify file exists on disk
        with open(test_file, "r") as f:
            assert "Datomic" in f.read()

        # Verify searchable
        search_resp = handle_request(
            {
                "method": "tools/call",
                "id": 51,
                "params": {
                    "name": "knowledge_search",
                    "arguments": {"query": "Datomic patterns"},
                },
            }
        )
        search_content = json.loads(search_resp["result"]["content"][0]["text"])
        assert any(r["file_path"] == test_file for r in search_content["results"])

    def test_write_overwrites_existing(self, monkeypatch, store, tmp_dir):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        test_file = os.path.join(tmp_dir, "overwrite.md")
        # Write once
        handle_request(
            {
                "method": "tools/call",
                "id": 52,
                "params": {
                    "name": "knowledge_write",
                    "arguments": {
                        "file_path": test_file,
                        "content": "Original content.",
                        "description": "Original",
                        "category": "service",
                    },
                },
            }
        )
        # Write again
        resp = handle_request(
            {
                "method": "tools/call",
                "id": 53,
                "params": {
                    "name": "knowledge_write",
                    "arguments": {
                        "file_path": test_file,
                        "content": "Updated content.",
                        "description": "Updated",
                        "category": "service",
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "updated"

        with open(test_file, "r") as f:
            assert f.read() == "Updated content."


class TestKnowledgeEdit:
    def test_edit_replaces_and_reindexes(self, monkeypatch, store, tmp_dir):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        test_file = os.path.join(tmp_dir, "edit.md")
        # Create file first
        handle_request(
            {
                "method": "tools/call",
                "id": 60,
                "params": {
                    "name": "knowledge_write",
                    "arguments": {
                        "file_path": test_file,
                        "content": "SAA handles authorization.",
                        "description": "SAA overview",
                        "category": "service",
                    },
                },
            }
        )
        # Edit it
        resp = handle_request(
            {
                "method": "tools/call",
                "id": 61,
                "params": {
                    "name": "knowledge_edit",
                    "arguments": {
                        "file_path": test_file,
                        "old_string": "authorization",
                        "new_string": "authorization and settlement",
                        "description": "SAA overview with settlement",
                        "category": "service",
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "updated"

        with open(test_file, "r") as f:
            assert "authorization and settlement" in f.read()

    def test_edit_string_not_found(self, monkeypatch, store, tmp_dir):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        test_file = os.path.join(tmp_dir, "edit2.md")
        with open(test_file, "w") as f:
            f.write("Some content.")

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 62,
                "params": {
                    "name": "knowledge_edit",
                    "arguments": {
                        "file_path": test_file,
                        "old_string": "nonexistent string",
                        "new_string": "replacement",
                        "description": "Test",
                        "category": "service",
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content

    def test_edit_file_not_found(self, monkeypatch, store):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 63,
                "params": {
                    "name": "knowledge_edit",
                    "arguments": {
                        "file_path": "/nonexistent/file.md",
                        "old_string": "x",
                        "new_string": "y",
                        "description": "Test",
                        "category": "service",
                    },
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content


class TestKnowledgeSearch:
    def test_search(self, monkeypatch, seeded_store):
        _patch_server(monkeypatch, seeded_store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 20,
                "params": {
                    "name": "knowledge_search",
                    "arguments": {"query": "authorization engine"},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert len(content["results"]) > 0

    def test_search_with_category(self, monkeypatch, seeded_store):
        _patch_server(monkeypatch, seeded_store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 21,
                "params": {
                    "name": "knowledge_search",
                    "arguments": {"query": "layers", "category": "pattern"},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert all(r["category"] == "pattern" for r in content["results"])

    def test_search_integer_coercion(self, monkeypatch, seeded_store):
        """MCP transport may send limit as string — server must coerce to int."""
        _patch_server(monkeypatch, seeded_store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 22,
                "params": {
                    "name": "knowledge_search",
                    "arguments": {"query": "SAA", "limit": "1"},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert len(content["results"]) <= 1


class TestKnowledgeGlossary:
    def test_glossary_all(self, monkeypatch, seeded_store):
        _patch_server(monkeypatch, seeded_store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 30,
                "params": {
                    "name": "knowledge_glossary",
                    "arguments": {},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert len(content["terms"]) >= 3

    def test_glossary_search(self, monkeypatch, seeded_store):
        _patch_server(monkeypatch, seeded_store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 31,
                "params": {
                    "name": "knowledge_glossary",
                    "arguments": {"term": "SAA"},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert any(t["term"] == "SAA" for t in content["terms"])


class TestKnowledgeRemove:
    def test_remove_existing(self, monkeypatch, seeded_store):
        _patch_server(monkeypatch, seeded_store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 40,
                "params": {
                    "name": "knowledge_remove",
                    "arguments": {"file_path": "/knowledge/services/saa.md"},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "removed"

    def test_remove_nonexistent(self, monkeypatch, store):
        _patch_server(monkeypatch, store)
        from knowledge_semantic.mcp_server import handle_request

        resp = handle_request(
            {
                "method": "tools/call",
                "id": 41,
                "params": {
                    "name": "knowledge_remove",
                    "arguments": {"file_path": "/nonexistent.md"},
                },
            }
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "not_found"
