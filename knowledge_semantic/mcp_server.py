"""
Knowledge Semantic MCP Server — semantic search over curated knowledge files.
=============================================================================
Install: claude mcp add knowledge-semantic -- python -m knowledge_semantic.mcp_server

Tools:
  knowledge_index     — push a file into ChromaDB with LLM-defined metadata
  knowledge_search    — semantic search across indexed files
  knowledge_glossary  — list or search glossary terms
  knowledge_remove    — remove a file from the index
"""

import sys
import json
import logging

from .store import KnowledgeStore
from .version import __version__

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
logger = logging.getLogger("knowledge_semantic")

_store = KnowledgeStore()


def tool_index(file_path, description, category, glossary_terms=None):
    """Read a file and index it in ChromaDB with metadata."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except OSError as e:
        return {"error": f"Cannot read file: {e}"}

    return _store.upsert(
        file_path=file_path,
        content=content,
        description=description,
        category=category,
        glossary_terms=glossary_terms or [],
    )


def tool_write(file_path, content, description, category, glossary_terms=None):
    """Write a knowledge file to disk and index it in ChromaDB atomically."""
    import os

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return {"error": f"Cannot write file: {e}"}

    return _store.upsert(
        file_path=file_path,
        content=content,
        description=description,
        category=category,
        glossary_terms=glossary_terms or [],
    )


def tool_edit(file_path, old_string, new_string, description, category, glossary_terms=None):
    """Edit a knowledge file (string replacement) and re-index in ChromaDB atomically."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except OSError as e:
        return {"error": f"Cannot read file: {e}"}

    if old_string not in content:
        return {"error": f"String to replace not found in {file_path}"}

    new_content = content.replace(old_string, new_string, 1)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        return {"error": f"Cannot write file: {e}"}

    return _store.upsert(
        file_path=file_path,
        content=new_content,
        description=description,
        category=category,
        glossary_terms=glossary_terms or [],
    )


def tool_search(query, category=None, limit=5):
    """Semantic search across indexed knowledge files."""
    results = _store.search(query=query, category=category, limit=limit)
    return {"query": query, "results": results, "count": len(results)}


def tool_glossary(term=None):
    """List or search glossary terms."""
    terms = _store.glossary(term=term)
    return {"terms": terms, "count": len(terms)}


def tool_remove(file_path):
    """Remove a file from the index."""
    return _store.remove(file_path)


TOOLS = {
    "knowledge_index": {
        "description": (
            "Index a knowledge file into ChromaDB with LLM-defined metadata. "
            "Reads the file content, computes embedding, stores with description, "
            "category, and glossary terms. Updates in place if already indexed."
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
                    "description": "One-line description of the file's content",
                },
                "category": {
                    "type": "string",
                    "description": "One of: domain, service, pattern, convention, framework, infrastructure, operations, workflow, claude-code, project, memory",
                },
                "glossary_terms": {
                    "type": "array",
                    "description": "List of glossary terms found in the file",
                    "items": {
                        "type": "object",
                        "properties": {
                            "term": {"type": "string"},
                            "aliases": {"type": "array", "items": {"type": "string"}},
                            "definition": {"type": "string"},
                        },
                        "required": ["term"],
                    },
                },
            },
            "required": ["file_path", "description", "category"],
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
                    "items": {
                        "type": "object",
                        "properties": {
                            "term": {"type": "string"},
                            "aliases": {"type": "array", "items": {"type": "string"}},
                            "definition": {"type": "string"},
                        },
                        "required": ["term"],
                    },
                },
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
                    "items": {
                        "type": "object",
                        "properties": {
                            "term": {"type": "string"},
                            "aliases": {"type": "array", "items": {"type": "string"}},
                            "definition": {"type": "string"},
                        },
                        "required": ["term"],
                    },
                },
            },
            "required": ["file_path", "old_string", "new_string", "description", "category"],
        },
        "handler": tool_edit,
    },
    "knowledge_search": {
        "description": (
            "Semantic search across all indexed knowledge files. "
            "Returns ranked file paths with similarity scores and metadata. "
            "Use Read tool on returned paths to get full content."
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
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 5)",
                },
            },
            "required": ["query"],
        },
        "handler": tool_search,
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
}


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
        except Exception:
            logger.exception(f"Tool error in {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": "Internal tool error"},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main():
    """MCP server main loop — read JSON-RPC from stdin, write responses to stdout."""
    logger.info("Knowledge Semantic MCP Server starting...")
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
