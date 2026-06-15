"""Tests for the domain registry module."""

import json
import os
import subprocess
import tempfile

import pytest

from knowledge_semantic.domains import (
    Domain,
    DomainRegistry,
    git_clone,
    git_pull,
    load_registry,
)


# ---------------------------------------------------------------------------
# Domain.knowledge_path
# ---------------------------------------------------------------------------


class TestDomainKnowledgePath:
    def test_git_path_dot_returns_path(self):
        d = Domain(slug="x", path="/repo", git_path=".")
        assert d.knowledge_path == "/repo"

    def test_git_path_empty_returns_path(self):
        d = Domain(slug="x", path="/repo", git_path="")
        assert d.knowledge_path == "/repo"

    def test_git_path_subdir(self):
        d = Domain(slug="x", path="/repo", git_path="knowledge")
        assert d.knowledge_path == "/repo/knowledge"

    def test_git_path_nested(self):
        d = Domain(slug="x", path="/repo", git_path="docs/knowledge")
        assert d.knowledge_path == "/repo/docs/knowledge"


# ---------------------------------------------------------------------------
# DomainRegistry.get
# ---------------------------------------------------------------------------


class TestDomainRegistryGet:
    def _registry(self):
        reg = DomainRegistry(default="personal")
        reg.domains["personal"] = Domain(slug="personal", path="/personal")
        reg.domains["deposit-platform"] = Domain(
            slug="deposit-platform",
            path="/deposit",
            git_url="https://github.com/nubank/knowledge-deposit-platform.git",
        )
        return reg

    def test_get_explicit(self):
        reg = self._registry()
        d = reg.get("deposit-platform")
        assert d.slug == "deposit-platform"

    def test_get_default_when_none(self):
        reg = self._registry()
        d = reg.get(None)
        assert d.slug == "personal"

    def test_get_unknown_raises(self):
        reg = self._registry()
        with pytest.raises(ValueError, match="Unknown domain"):
            reg.get("does-not-exist")

    def test_list_all_marks_default(self):
        reg = self._registry()
        listing = reg.list_all()
        defaults = [e for e in listing if e["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["slug"] == "personal"

    def test_list_all_includes_knowledge_path(self):
        reg = DomainRegistry(default="personal")
        reg.domains["personal"] = Domain(slug="personal", path="/repo", git_path="knowledge")
        listing = reg.list_all()
        assert listing[0]["knowledge_path"] == "/repo/knowledge"


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------


class TestLoadRegistry:
    def test_loads_from_json_file(self, tmp_path, monkeypatch):
        cfg = {
            "default": "work",
            "domains": {
                "work": {
                    "path": str(tmp_path / "work"),
                    "git_url": "https://github.com/example/work.git",
                    "git_path": "knowledge",
                },
                "personal": {
                    "path": str(tmp_path / "personal"),
                    "git_path": ".",
                },
            },
        }
        cfg_path = tmp_path / "domains.json"
        cfg_path.write_text(json.dumps(cfg))
        # Patch _CONFIG_SEARCH_PATHS directly (evaluated at import time)
        monkeypatch.setattr(
            "knowledge_semantic.domains._CONFIG_SEARCH_PATHS",
            [str(cfg_path)],
        )
        reg = load_registry()
        assert reg.default == "work"
        assert "work" in reg.domains
        assert "personal" in reg.domains
        assert reg.domains["work"].git_url == "https://github.com/example/work.git"
        assert reg.domains["work"].git_path == "knowledge"
        assert reg.domains["personal"].git_path == "."

    def test_falls_back_to_builtin_when_no_file(self, monkeypatch, tmp_path):
        # Point to non-existent paths
        monkeypatch.setenv("KNOWLEDGE_DOMAINS_FILE", str(tmp_path / "missing.json"))
        monkeypatch.setattr(
            "knowledge_semantic.domains._CONFIG_SEARCH_PATHS",
            [str(tmp_path / "missing.json"), str(tmp_path / "also-missing.json")],
        )
        reg = load_registry()
        assert "personal" in reg.domains
        assert reg.default == "personal"

    def test_tilde_expansion(self, tmp_path, monkeypatch):
        cfg = {
            "default": "personal",
            "domains": {
                "personal": {
                    "path": "~/some/path",
                    "git_path": "knowledge",
                }
            },
        }
        cfg_path = tmp_path / "domains.json"
        cfg_path.write_text(json.dumps(cfg))
        monkeypatch.setenv("KNOWLEDGE_DOMAINS_FILE", str(cfg_path))
        reg = load_registry()
        assert not reg.domains["personal"].path.startswith("~")
        assert reg.domains["personal"].path.startswith(os.path.expanduser("~"))


# ---------------------------------------------------------------------------
# git_pull
# ---------------------------------------------------------------------------


class TestGitPull:
    def test_pull_ok(self, tmp_path):
        # Init a bare repo, add one commit so pull has something to track
        origin = tmp_path / "origin"
        origin.mkdir()
        subprocess.run(["git", "init", str(origin)], check=True, capture_output=True)
        readme = origin / "README.md"
        readme.write_text("hello")
        subprocess.run(
            ["git", "-C", str(origin), "config", "user.email", "test@test.com"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(origin), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(origin), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(origin), "commit", "-m", "init"],
            check=True, capture_output=True,
        )

        clone = tmp_path / "clone"
        subprocess.run(
            ["git", "clone", str(origin), str(clone)], check=True, capture_output=True
        )
        d = Domain(slug="test", path=str(clone))
        result = git_pull(d)
        assert result["status"] == "ok"
        assert result["domain"] == "test"

    def test_pull_missing_path(self, tmp_path):
        d = Domain(slug="x", path=str(tmp_path / "does-not-exist"))
        result = git_pull(d)
        assert result["status"] == "error"
        assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# git_clone
# ---------------------------------------------------------------------------


class TestGitClone:
    def test_clone_no_git_url(self, tmp_path):
        d = Domain(slug="x", path=str(tmp_path / "dest"))
        result = git_clone(d)
        assert result["status"] == "error"
        assert "No git_url" in result["error"]

    def test_clone_already_cloned(self, tmp_path):
        dest = tmp_path / "dest"
        dest.mkdir()
        git_dir = dest / ".git"
        git_dir.mkdir()
        d = Domain(slug="x", path=str(dest), git_url="https://github.com/x/y.git")
        result = git_clone(d)
        assert result["status"] == "already_cloned"

    def test_clone_invalid_url(self, tmp_path):
        dest = tmp_path / "dest"
        d = Domain(
            slug="x",
            path=str(dest),
            git_url="https://github.com/invalid-user-xyzxyz/no-such-repo-abc.git",
        )
        result = git_clone(d)
        assert result["status"] == "error"
