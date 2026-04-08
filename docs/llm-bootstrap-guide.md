# LLM Bootstrap Guide

You are reading this because your user sent you this link. This document tells you how to use the Knowledge Semantic MCP server — a persistent semantic search layer over a collection of markdown files. This is your long-term memory.

Read this document fully, then follow the setup instructions. Once configured, you will be able to search, create, edit, and manage knowledge files that persist across sessions.

## Knowledge Base

Knowledge files are markdown documents organized in a directory (default: `~/knowledge/`, or wherever `KNOWLEDGE_PATH` is configured). The search index is stored in `.chromadb/` inside that directory and persists across sessions. Embeddings are computed automatically — you search by meaning, not by filename.

### Tools

**Read tools:**

- `knowledge_search(query, category?, limit?)` — semantic search across all indexed files. Returns ranked file paths with similarity scores and metadata. Read the returned paths for full content.
- `knowledge_glossary(term?)` — search glossary terms and aliases across all indexed files. Omit `term` to list everything.

**Write tools:**

- `knowledge_write(file_path, content, description, category, glossary_terms?)` — create or overwrite a knowledge file and auto-index in one atomic call. The file is written to disk and indexed in ChromaDB simultaneously.
- `knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms?)` — edit a knowledge file (string replacement) and auto-re-index. One call, both the file and the index stay in sync.
- `knowledge_index(file_path, description, category, glossary_terms?)` — index an existing file without modifying it. Use this for bulk indexing or re-indexing.
- `knowledge_remove(file_path)` — remove a file from the search index.

### Rules

- Always search before saying "I don't know." Use `knowledge_glossary` for terms and acronyms, `knowledge_search` for broader queries. The semantic embeddings find relevant files even when the wording differs from what is stored.
- All knowledge file writes go through `knowledge_write` or `knowledge_edit`. Never use raw file operations on knowledge files — the search index goes stale silently and results degrade.
- When you learn something reusable during a session, offer to persist it via `knowledge_write`.
- Provide good descriptions and accurate categories when indexing. Vague metadata leads to poor retrieval.
- Include `glossary_terms` for key terminology in each file so that `knowledge_glossary` can resolve acronyms and aliases.

### Categories

Use one of these categories when indexing files:

- **domain** — business domain concepts, rules, and glossary
- **service** — microservice documentation, APIs, dependencies
- **pattern** — reusable technical patterns (retry, circuit breaker, saga)
- **convention** — coding standards, style guides, PR rules
- **framework** — framework-specific knowledge (React, Spring, etc.)
- **infrastructure** — deployment, CI/CD, cloud resources
- **operations** — runbooks, incident procedures, monitoring
- **workflow** — team processes, review flows, release procedures
- **project** — active project context, decisions, checkpoints
- **memory** — persistent user preferences and feedback

### First Session Bootstrap

If the knowledge base has never been indexed (ChromaDB is empty and all searches return zero results), the user will ask you to "index the knowledge base." When this happens:

1. List all markdown files in the knowledge directory.
2. Read each file and analyze its content.
3. Call `knowledge_index` for each file with a one-line description, the appropriate category, and any glossary terms found in the content.

This is a one-time process. On subsequent sessions, ChromaDB loads the persisted index from `.chromadb/` and search works immediately.

---

## Setup

Ask your user to install the MCP server if it is not already available. The steps depend on which tool you are running in.

### Claude Code

Ask the user to run:

```bash
pip install -e /path/to/knowledge-semantic
claude mcp add --scope user knowledge-semantic -- python -m knowledge_semantic.mcp_server
```

Then add the Tools, Rules, and Categories sections above to the user's `CLAUDE.md` (global at `~/.claude/CLAUDE.md` or per-project).

### Cursor

Ask the user to:

1. Install: `pip install -e /path/to/knowledge-semantic`
2. Register the MCP server in Settings > MCP Servers with the command: `python -m knowledge_semantic.mcp_server`

Then add the Tools, Rules, and Categories sections above to `.cursorrules` at the project root.

### Windsurf

Ask the user to:

1. Install: `pip install -e /path/to/knowledge-semantic`
2. Register the MCP server in Settings > MCP with the command: `python -m knowledge_semantic.mcp_server`

Then add the Tools, Rules, and Categories sections above to `.windsurfrules` at the project root.

### GitHub Copilot

Ask the user to:

1. Install: `pip install -e /path/to/knowledge-semantic`
2. Add to `.github/copilot-mcp.json`:

```json
{
  "servers": {
    "knowledge-semantic": {
      "command": "python",
      "args": ["-m", "knowledge_semantic.mcp_server"]
    }
  }
}
```

Then add the Tools, Rules, and Categories sections above to `.github/copilot-instructions.md`.

### Environment Variables

If the user's knowledge files are not at the default location (`~/knowledge`), ask them to set these environment variables in the MCP server configuration:

- `KNOWLEDGE_PATH` — root directory of the knowledge files
- `CHROMADB_PATH` — where ChromaDB stores its data (default: `$KNOWLEDGE_PATH/.chromadb`)
