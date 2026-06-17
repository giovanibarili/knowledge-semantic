"""
Knowledge Semantic MCP Server — semantic search over curated knowledge files.
=============================================================================
Install: claude mcp add knowledge-semantic -- python -m knowledge_semantic.mcp_server

Tools:
  knowledge_index          — push a file into ChromaDB with LLM-defined metadata
  knowledge_write          — write a file to disk and auto-index
  knowledge_edit           — edit a file (string replacement) and re-index
  knowledge_search         — semantic search across indexed files
  knowledge_hybrid_search  — vector + BM25 fused via RRF
  knowledge_glossary        — list or search glossary terms
  knowledge_remove          — remove a file from the index
  knowledge_reindex         — bulk re-index a directory of markdown files
  knowledge_status          — report index health (stale, orphaned, totals)
  knowledge_domains         — list configured domains
  knowledge_pull            — git pull one or all domains
"""

import sys
import json
import logging
import os

from .frontmatter import extract_index_metadata
from .store import KnowledgeStore
from .domains import DomainRegistry, load_registry, git_pull, git_clone
from .version import __version__

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
logger = logging.getLogger("knowledge_semantic")

_store = KnowledgeStore()
_registry: DomainRegistry = load_registry()

_DOMAIN_PARAM = {
    "type": "string",
    "description": (
        "Domain slug (e.g. 'personal', 'deposit-platform'). "
        "Omit to use the default domain. "
        "For writes, always specify the target domain explicitly."
    ),
}

_TYPE_PARAM = {
    "type": "string",
    "description": (
        "OKF artifact type (open vocabulary, e.g. Pattern, Service, Runbook, "
        "Concept, Reference). Optional — extracted from frontmatter if omitted."
    ),
}

_GLOSSARY_TERMS_ITEMS = {
    "type": "object",
    "properties": {
        "term": {"type": "string"},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "definition": {"type": "string"},
    },
    "required": ["term"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_file_path(file_path: str, domain_slug: str | None) -> str:
    """If file_path is relative, resolve against the domain's knowledge_path."""
    if os.path.isabs(file_path):
        return file_path
    domain = _registry.get(domain_slug)
    return os.path.join(domain.knowledge_path, file_path)


def _effective_domain(domain_slug: str | None) -> str:
    """Return the effective domain slug (explicit or default)."""
    return domain_slug or _registry.default


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def tool_index(file_path, description=None, category=None, glossary_terms=None,
               project=None, domain=None, type=None):
    """Read a file and index it in ChromaDB with metadata."""
    domain_slug = _effective_domain(domain)
    resolved = _resolve_file_path(file_path, domain_slug)
    try:
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {resolved}"}
    except OSError as e:
        return {"error": f"Cannot read file: {e}"}

    fm = extract_index_metadata(content)

    effective_desc = description or (fm.get("description") if fm else None) or resolved
    effective_cat = category or (fm.get("category") if fm else None) or "unknown"
    effective_terms = glossary_terms or (fm.get("glossary_terms") if fm else None) or []
    effective_type = type or (fm.get("type") if fm else None)

    return _store.upsert(
        file_path=resolved,
        content=content,
        description=effective_desc,
        category=effective_cat,
        glossary_terms=effective_terms,
        project=project or (fm.get("project") if fm else None),
        domain=domain_slug,
        type=effective_type,
    )


def tool_write(file_path, content, description, category, glossary_terms=None,
               project=None, domain=None, type=None):
    """Write a knowledge file to disk and index it in ChromaDB atomically."""
    domain_slug = _effective_domain(domain)
    resolved = _resolve_file_path(file_path, domain_slug)
    try:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return {"error": f"Cannot write file: {e}"}

    return _store.upsert(
        file_path=resolved,
        content=content,
        description=description,
        category=category,
        glossary_terms=glossary_terms or [],
        project=project,
        domain=domain_slug,
        type=type,
    )


def tool_edit(file_path, old_string, new_string, description, category,
              glossary_terms=None, project=None, domain=None, type=None):
    """Edit a knowledge file (string replacement) and re-index in ChromaDB atomically."""
    domain_slug = _effective_domain(domain)
    resolved = _resolve_file_path(file_path, domain_slug)
    try:
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {resolved}"}
    except OSError as e:
        return {"error": f"Cannot read file: {e}"}

    if old_string not in content:
        return {"error": f"String to replace not found in {resolved}"}

    new_content = content.replace(old_string, new_string, 1)

    try:
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        return {"error": f"Cannot write file: {e}"}

    return _store.upsert(
        file_path=resolved,
        content=new_content,
        description=description,
        category=category,
        glossary_terms=glossary_terms or [],
        project=project,
        domain=domain_slug,
        type=type,
    )


def tool_search(query, category=None, project=None, domain=None, type=None, limit=5):
    """Semantic search across indexed knowledge files."""
    results = _store.search(
        query=query, category=category, project=project,
        domain=domain, type=type, limit=limit,
    )
    return {"query": query, "results": results, "count": len(results)}


def tool_hybrid_search(query, category=None, project=None, domain=None, type=None, limit=5):
    """Hybrid (vector + BM25, fused via RRF) search across indexed knowledge."""
    results = _store.hybrid_search(
        query=query, category=category, project=project,
        domain=domain, type=type, limit=limit,
    )
    return {"query": query, "results": results, "count": len(results)}


def tool_glossary(term=None):
    """List or search glossary terms."""
    terms = _store.glossary(term=term)
    return {"terms": terms, "count": len(terms)}


def tool_remove(file_path):
    """Remove a file from the index."""
    return _store.remove(file_path)


def tool_reindex(directory=None, domain=None, recursive=True):
    """Walk a directory (or a domain's knowledge_path) and index/update all .md files."""
    domain_slug = _effective_domain(domain) if domain is not None else None

    if directory:
        target_dir = directory
        effective_domain_slug = domain_slug
    elif domain_slug:
        d = _registry.get(domain_slug)
        target_dir = d.knowledge_path
        effective_domain_slug = domain_slug
    else:
        # No directory and no domain — fall back to default domain
        d = _registry.get(_registry.default)
        target_dir = d.knowledge_path
        effective_domain_slug = _registry.default

    return _store.reindex(
        directory=target_dir, recursive=recursive, domain=effective_domain_slug,
    )


def tool_status():
    """Report index health."""
    return _store.status()


def tool_domains():
    """List all configured knowledge domains."""
    return {
        "default": _registry.default,
        "domains": _registry.list_all(),
        "count": len(_registry.domains),
    }


def tool_pull(domain=None):
    """Git pull one or all domains.

    If domain is given, pulls only that domain's repo.
    If omitted, pulls all configured domains that have a git_url.
    """
    if domain:
        d = _registry.get(domain)
        return git_pull(d)

    results = []
    for d in _registry.domains.values():
        results.append(git_pull(d))
    return {"results": results, "count": len(results)}


def tool_clone(domain):
    """Clone a domain's git_url into its configured path."""
    d = _registry.get(domain)
    return git_clone(d)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = {
    "knowledge_index": {
        "description": (
            "Index a knowledge file into ChromaDB with LLM-defined metadata. "
            "Reads the file content, computes embedding, stores with description, "
            "category, and glossary terms. Updates in place if already indexed. "
            "If description/category are omitted, extracts them from YAML frontmatter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the markdown file",
                },
                "description": {
                    "type": "string",
                    "description": "One-line description (optional — extracted from frontmatter if omitted)",
                },
                "category": {
                    "type": "string",
                    "description": "Category (optional — extracted from frontmatter if omitted). One of: domain, service, pattern, convention, framework, infrastructure, operations, workflow, claude-code, project, memory",
                },
                "glossary_terms": {
                    "type": "array",
                    "description": "List of glossary terms (optional — extracted from frontmatter if omitted)",
                    "items": _GLOSSARY_TERMS_ITEMS,
                },
                "project": {
                    "type": "string",
                    "description": "Project/repo name for scoping (optional — omit for global knowledge)",
                },
                "domain": _DOMAIN_PARAM,
                "type": _TYPE_PARAM,
            },
            "required": ["file_path"],
        },
        "handler": tool_index,
    },
    "knowledge_write": {
        "description": (
            "Write a knowledge file to disk and auto-index in ChromaDB. "
            "Creates or overwrites the file, then indexes with the provided metadata. "
            "Use this instead of the Write tool for knowledge files to keep the index in sync."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the markdown file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file",
                },
                "description": {
                    "type": "string",
                    "description": "One-line description of the file's content",
                },
                "category": {
                    "type": "string",
                    "description": "One of: domain, service, pattern, convention, framework, infrastructure, operations, workflow, claude-code, project, memory",
                },
                "glossary_terms": {
                    "type": "array",
                    "description": "List of glossary terms found in the file",
                    "items": _GLOSSARY_TERMS_ITEMS,
                },
                "project": {
                    "type": "string",
                    "description": "Project/repo name for scoping (optional — omit for global knowledge)",
                },
                "domain": _DOMAIN_PARAM,
                "type": _TYPE_PARAM,
            },
            "required": ["file_path", "content", "description", "category"],
        },
        "handler": tool_write,
    },
    "knowledge_edit": {
        "description": (
            "Edit a knowledge file (string replacement) and auto-re-index in ChromaDB. "
            "Replaces the first occurrence of old_string with new_string, then re-indexes. "
            "Use this instead of the Edit tool for knowledge files to keep the index in sync."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the markdown file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement string",
                },
                "description": {
                    "type": "string",
                    "description": "One-line description of the file's content (after edit)",
                },
                "category": {
                    "type": "string",
                    "description": "One of: domain, service, pattern, convention, framework, infrastructure, operations, workflow, claude-code, project, memory",
                },
                "glossary_terms": {
                    "type": "array",
                    "description": "List of glossary terms found in the file",
                    "items": _GLOSSARY_TERMS_ITEMS,
                },
                "project": {
                    "type": "string",
                    "description": "Project/repo name for scoping (optional — omit for global knowledge)",
                },
                "domain": _DOMAIN_PARAM,
                "type": _TYPE_PARAM,
            },
            "required": ["file_path", "old_string", "new_string", "description", "category"],
        },
        "handler": tool_edit,
    },
    "knowledge_search": {
        "description": (
            "Semantic search across all indexed knowledge files. "
            "Returns ranked file paths with similarity scores and metadata. "
            "Use Read tool on returned paths to get full content. "
            "Omit domain to search cross-domain (all)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "category": {
                    "type": "string",
                    "description": "Filter results to a specific category (optional)",
                },
                "project": {
                    "type": "string",
                    "description": "Filter results to a specific project/repo (optional — omit to search all)",
                },
                "domain": {
                    **_DOMAIN_PARAM,
                    "description": "Filter to a specific domain (optional — omit for cross-domain search)",
                },
                "type": {
                    **_TYPE_PARAM,
                    "description": "Filter results to a specific OKF type (optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 5)",
                },
            },
            "required": ["query"],
        },
        "handler": tool_search,
    },
    "knowledge_hybrid_search": {
        "description": (
            "Hybrid semantic + lexical (BM25) search across indexed knowledge files. "
            "Vector retrieves paraphrases and conceptual matches; BM25 retrieves exact "
            "identifiers, acronyms, and kebab-case symbols. Results are fused via "
            "Reciprocal Rank Fusion (RRF). Each hit is decorated with rrf_score, "
            "vec_rank, bm25_rank, and an in_both flag. "
            "Omit domain to search cross-domain (all)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (natural language or mixed with exact identifiers)",
                },
                "category": {
                    "type": "string",
                    "description": "Filter results to a specific category (optional)",
                },
                "project": {
                    "type": "string",
                    "description": "Filter results to a specific project/repo (optional)",
                },
                "domain": {
                    **_DOMAIN_PARAM,
                    "description": "Filter to a specific domain (optional — omit for cross-domain search)",
                },
                "type": {
                    **_TYPE_PARAM,
                    "description": "Filter results to a specific OKF type (optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 5)",
                },
            },
            "required": ["query"],
        },
        "handler": tool_hybrid_search,
    },
    "knowledge_glossary": {
        "description": (
            "List or search glossary terms across all indexed knowledge files. "
            "Returns term, aliases, definition, and source file for each match."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "Search string to match against terms and aliases (optional — omit for all terms)",
                },
            },
        },
        "handler": tool_glossary,
    },
    "knowledge_remove": {
        "description": "Remove a knowledge file from the search index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The file path used as document ID when indexed",
                },
            },
            "required": ["file_path"],
        },
        "handler": tool_remove,
    },
    "knowledge_reindex": {
        "description": (
            "Bulk re-index a directory of markdown files. "
            "Pass domain to resolve the directory from the domain config automatically. "
            "Pass directory for an explicit path. "
            "Skips files whose mtime is older than their last indexed timestamp. "
            "Use after git pull, branch switch, or to bootstrap a new knowledge base."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Absolute path to the directory to scan (optional — resolved from domain if omitted)",
                },
                "domain": {
                    **_DOMAIN_PARAM,
                    "description": "Domain to reindex (resolves directory from config). Omit if providing directory.",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Walk subdirectories recursively (default true)",
                },
            },
        },
        "handler": tool_reindex,
    },
    "knowledge_status": {
        "description": (
            "Report index health: total indexed files, stale files (disk mtime > indexed_at), "
            "and orphaned entries (in index but deleted from disk). "
            "Use at session start to detect drift and decide if reindex is needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "handler": tool_status,
    },
    "knowledge_domains": {
        "description": (
            "List all configured knowledge domains with their paths, git URLs, and default flag. "
            "Use to discover available domains before write/reindex operations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "handler": tool_domains,
    },
    "knowledge_pull": {
        "description": (
            "Run git pull on one or all knowledge domains. "
            "Pass domain slug to pull a single domain; omit to pull all. "
            "Returns pull status per domain. Use before reindex to get latest content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain slug to pull (optional — omits pulls all domains)",
                },
            },
        },
        "handler": tool_pull,
    },
    "knowledge_clone": {
        "description": (
            "Clone a domain's git repository into its configured local path. "
            "Skips silently if already cloned. Requires git_url in domain config."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain slug to clone",
                },
            },
            "required": ["domain"],
        },
        "handler": tool_clone,
    },
}


# ---------------------------------------------------------------------------
# JSON-RPC loop
# ---------------------------------------------------------------------------

def handle_request(request):
    """Route a JSON-RPC request to the appropriate handler."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "knowledge-semantic", "version": __version__},
            },
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {"name": n, "description": t["description"], "inputSchema": t["input_schema"]}
                    for n, t in TOOLS.items()
                ]
            },
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
        schema_props = TOOLS[tool_name]["input_schema"].get("properties", {})
        # Strip internal MCP SDK params (e.g. __sessionId) that aren't in our schema
        tool_args = {k: v for k, v in tool_args.items() if not k.startswith("__")}
        for key, value in list(tool_args.items()):
            prop_schema = schema_props.get(key, {})
            declared_type = prop_schema.get("type")
            if declared_type == "integer" and not isinstance(value, int):
                tool_args[key] = int(value)
            elif declared_type == "number" and not isinstance(value, (int, float)):
                tool_args[key] = float(value)
        try:
            result = TOOLS[tool_name]["handler"](**tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
            }
        except Exception as exc:
            logger.exception(f"Tool error in {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": f"Internal tool error: {type(exc).__name__}: {exc}"},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main():
    """MCP server main loop — read JSON-RPC from stdin, write responses to stdout."""
    logger.info("Knowledge Semantic MCP Server starting...")
    logger.info(f"Domains: {list(_registry.domains.keys())} (default: {_registry.default})")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
