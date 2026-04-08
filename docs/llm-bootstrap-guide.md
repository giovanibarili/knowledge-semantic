# LLM Bootstrap Guide

This document is meant to be included in your LLM agent's system prompt or configuration file. Copy the sections you need into your `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, or `.github/copilot-instructions.md`. The text below is written for the LLM to read directly.

---

## Knowledge Base

You have access to a persistent knowledge base through the Knowledge Semantic MCP server. This is your long-term memory — a collection of markdown files indexed with semantic embeddings. You can search by meaning, not just by filename.

Knowledge files live at `~/knowledge/` (or wherever `KNOWLEDGE_PATH` is configured). The search index is stored in `.chromadb/` inside that directory and persists across sessions.

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

## Per-Tool Configuration

The section above is the generic content. Below are instructions for adding it to specific tools.

### Claude Code

Add the "Knowledge Base" section above to your `CLAUDE.md` file (global at `~/.claude/CLAUDE.md` or per-project).

Register the MCP server:

```bash
claude mcp add --scope user knowledge-semantic -- python -m knowledge_semantic.mcp_server
```

### Cursor

Add the "Knowledge Base" section above to `.cursorrules` at your project root. Cursor injects this into the system prompt automatically.

Register the MCP server in Settings > MCP Servers with the command:

```
python -m knowledge_semantic.mcp_server
```

### Windsurf

Add the "Knowledge Base" section above to `.windsurfrules` at your project root.

Register the MCP server in Settings > MCP with the command:

```
python -m knowledge_semantic.mcp_server
```

### GitHub Copilot

Add the "Knowledge Base" section above to `.github/copilot-instructions.md` in your repository.

Register the MCP server in `.github/copilot-mcp.json`:

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

### Environment Variables

Set these if your knowledge files or ChromaDB data are not at the default locations:

- `KNOWLEDGE_PATH` — root directory of your knowledge files (default: `~/knowledge`)
- `CHROMADB_PATH` — where ChromaDB stores its data (default: `$KNOWLEDGE_PATH/.chromadb`)

Example with Claude Code:

```bash
claude mcp add --scope user knowledge-semantic -e KNOWLEDGE_PATH=/path/to/knowledge -e CHROMADB_PATH=/path/to/.chromadb -- python -m knowledge_semantic.mcp_server
```
