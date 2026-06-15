"""
domains.py — Multi-domain registry for knowledge-semantic.

A domain maps a slug to a local path (and optionally a git remote + sub-path
within that repo).  All domains share a single ChromaDB instance; the slug is
stored as metadata on every document so reads can be filtered by domain while
writes always target an explicit one.

Configuration is loaded (in priority order) from:
  1. KNOWLEDGE_DOMAINS_FILE env var  → path to a JSON file
  2. ~/.jarvis/knowledge-domains.json
  3. ~/.knowledge-domains.json
  4. Built-in default (personal domain pointing at claude-dotfiles/knowledge/)

JSON schema
-----------
{
  "default": "personal",
  "domains": {
    "personal": {
      "path": "~/dev/personal/claude-dotfiles",
      "git_url": "https://github.com/giovanibarili/claude-dotfiles.git",
      "git_path": "knowledge"          ← sub-path inside the repo; "." means root
    },
    "deposit-platform": {
      "path": "~/dev/personal/knowledge-deposit-platform",
      "git_url": "https://github.com/nubank/knowledge-deposit-platform.git",
      "git_path": "."
    }
  }
}

Fields
------
path       — local root of the cloned repo (required). Expanded with ~.
git_url    — remote to clone from / pull (optional).
git_path   — relative sub-path within the repo that holds .md files (optional,
             default ".").  "knowledge" means <path>/knowledge/.
             Writes and reindex use <path>/<git_path>/ as the working directory.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("knowledge_semantic")

_CONFIG_SEARCH_PATHS = [
    os.environ.get("KNOWLEDGE_DOMAINS_FILE", ""),
    os.path.expanduser("~/.jarvis/knowledge-domains.json"),
    os.path.expanduser("~/.knowledge-domains.json"),
]

_BUILTIN_DEFAULT = {
    "default": "personal",
    "domains": {
        "personal": {
            "path": "~/dev/personal/claude-dotfiles",
            "git_path": "knowledge",
        }
    },
}


@dataclass
class Domain:
    slug: str
    path: str           # absolute, expanded
    git_url: Optional[str] = None
    git_path: str = "."  # relative sub-path within path

    @property
    def knowledge_path(self) -> str:
        """Absolute path to the knowledge directory (path + git_path)."""
        if self.git_path in (".", ""):
            return self.path
        return os.path.join(self.path, self.git_path)


@dataclass
class DomainRegistry:
    domains: Dict[str, Domain] = field(default_factory=dict)
    default: str = "personal"

    def get(self, slug: Optional[str] = None) -> Domain:
        target = slug or self.default
        if target not in self.domains:
            available = list(self.domains.keys())
            raise ValueError(
                f"Unknown domain '{target}'. Available: {available}"
            )
        return self.domains[target]

    def list_all(self):
        return [
            {
                "slug": d.slug,
                "path": d.path,
                "knowledge_path": d.knowledge_path,
                "git_url": d.git_url,
                "git_path": d.git_path,
                "is_default": d.slug == self.default,
            }
            for d in self.domains.values()
        ]


def _load_config() -> dict:
    for candidate in _CONFIG_SEARCH_PATHS:
        if not candidate:
            continue
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Loaded domain config from {candidate}")
                return data
            except Exception as e:
                logger.warning(f"Failed to load {candidate}: {e}")
    logger.info("No domain config found — using built-in default (personal)")
    return _BUILTIN_DEFAULT


def load_registry() -> DomainRegistry:
    cfg = _load_config()
    registry = DomainRegistry(default=cfg.get("default", "personal"))
    for slug, entry in cfg.get("domains", {}).items():
        raw_path = entry.get("path", "")
        if not raw_path:
            logger.warning(f"Domain '{slug}' has no path — skipping")
            continue
        registry.domains[slug] = Domain(
            slug=slug,
            path=os.path.expanduser(raw_path),
            git_url=entry.get("git_url"),
            git_path=entry.get("git_path", "."),
        )
    if not registry.domains:
        # Fallback: inject personal from built-in
        d = _BUILTIN_DEFAULT["domains"]["personal"]
        registry.domains["personal"] = Domain(
            slug="personal",
            path=os.path.expanduser(d["path"]),
            git_path=d.get("git_path", "knowledge"),
        )
    return registry


def git_pull(domain: Domain) -> dict:
    """Run git pull inside domain.path. Returns status dict."""
    if not os.path.isdir(domain.path):
        return {"domain": domain.slug, "status": "error", "error": f"Path not found: {domain.path}"}
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=domain.path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return {"domain": domain.slug, "status": "ok", "output": result.stdout.strip()}
        else:
            return {
                "domain": domain.slug,
                "status": "error",
                "error": result.stderr.strip() or result.stdout.strip(),
            }
    except subprocess.TimeoutExpired:
        return {"domain": domain.slug, "status": "error", "error": "git pull timed out"}
    except Exception as e:
        return {"domain": domain.slug, "status": "error", "error": str(e)}


def git_clone(domain: Domain) -> dict:
    """Clone domain.git_url into domain.path. Skips if already cloned."""
    if not domain.git_url:
        return {"domain": domain.slug, "status": "error", "error": "No git_url configured"}
    if os.path.isdir(os.path.join(domain.path, ".git")):
        return {"domain": domain.slug, "status": "already_cloned", "path": domain.path}
    parent = os.path.dirname(domain.path)
    os.makedirs(parent, exist_ok=True)
    try:
        result = subprocess.run(
            ["git", "clone", domain.git_url, domain.path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return {"domain": domain.slug, "status": "cloned", "path": domain.path}
        else:
            return {
                "domain": domain.slug,
                "status": "error",
                "error": result.stderr.strip() or result.stdout.strip(),
            }
    except subprocess.TimeoutExpired:
        return {"domain": domain.slug, "status": "error", "error": "git clone timed out"}
    except Exception as e:
        return {"domain": domain.slug, "status": "error", "error": str(e)}
