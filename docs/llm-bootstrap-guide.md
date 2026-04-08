# LLM Bootstrap Guide

Your LLM coding agent does not automatically know that a knowledge base exists or how to use it. You need to add instructions to its system prompt (or equivalent configuration file) so the agent discovers the MCP tools and follows the right usage patterns. This guide explains the generic pattern and provides copy-paste snippets for popular tools.

## The Pattern

Every LLM agent configuration needs three blocks of instructions.

### 1. Where the knowledge lives

Tell the agent the MCP server name and the root path of knowledge files. This is how the agent knows the tools exist and where to find the underlying markdown files when it needs to read full content.

```
The Knowledge Semantic MCP server (`knowledge_search`, `knowledge_glossary`, etc.) is available.
Knowledge files live at ~/path/to/knowledge/.
```

### 2. When to use which tool

Define rules so the agent reaches for the right tool at the right time.

- Use `knowledge_search(query)` before saying "I don't know." Semantic search finds relevant files even when the wording differs from what is stored.
- Use `knowledge_glossary(term)` to look up acronyms, terms, and aliases.
- Use `knowledge_write(path, content, description, category)` to create new knowledge files. This writes to disk AND indexes in ChromaDB in one atomic call.
- Use `knowledge_edit(path, old_string, new_string, description, category)` to update existing knowledge files. This edits the file AND re-indexes atomically.
- Never use raw file writes for knowledge files. If you bypass the MCP tools, the search index goes stale and results degrade silently.

### 3. How to maintain the index

Rules for keeping knowledge fresh over time.

- All knowledge writes go through the MCP tools (`knowledge_write`, `knowledge_edit`), never raw file operations.
- When the agent learns something reusable during a session, it should persist it via `knowledge_write`.
- Good descriptions and accurate categories power the search. Vague metadata leads to poor retrieval.
- Include `glossary_terms` for key terminology in each file so that `knowledge_glossary` can resolve acronyms and aliases.

## Bootstrap Flow

### First session (empty knowledge base)

1. The LLM agent starts and the MCP server starts as a subprocess.
2. ChromaDB is empty. All search queries return zero results.
3. Tell the agent: "Index the knowledge base."
4. The agent reads each markdown file, analyzes its content, and calls `knowledge_index` with a description, category, and glossary terms for each file.
5. This is a one-time process. It takes a few minutes for around 50 files.

### Subsequent sessions

1. The MCP server starts and ChromaDB loads persisted data from `.chromadb/`.
2. Search works immediately with no re-indexing needed.
3. The agent uses `knowledge_search` to find context and `knowledge_write`/`knowledge_edit` to update files as it works.

### On a fresh machine

1. Clone your repo. This gets your knowledge files plus `.chromadb/` if you track it in git (or you regenerate if it is gitignored).
2. Install knowledge-semantic: `pip install -e /path/to/knowledge-semantic`
3. Register the MCP server with your tool (see MCP Server Registration below).
4. If `.chromadb/` was gitignored, run a one-time "index the knowledge base" as described above.

## Tool-Specific Snippets

Each snippet below is complete and self-contained. Copy-paste it into the appropriate config file for your tool.

### Claude Code (`CLAUDE.md`)

Add this to your `CLAUDE.md` file (global at `~/.claude/CLAUDE.md` or per-project):

```markdown
## Knowledge Base

The Knowledge Semantic MCP server provides semantic search over your knowledge files.

### MCP Tools
- `knowledge_search(query, category?, limit?)` — semantic search across all indexed files. Returns ranked paths with scores. Use Read on returned paths for full content.
- `knowledge_glossary(term?)` — search glossary terms and aliases. Omit term to list all.
- `knowledge_write(file_path, content, description, category, glossary_terms?)` — create/overwrite a file and auto-index.
- `knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms?)` — edit a file and auto-re-index.
- `knowledge_index(file_path, description, category, glossary_terms?)` — index an existing file without modifying it.
- `knowledge_remove(file_path)` — remove from the search index.

### Rules
- Always search before saying "I don't know": `knowledge_glossary` for terms, `knowledge_search` for content
- All knowledge file writes go through `knowledge_write` / `knowledge_edit` — never raw file operations
- When learning something reusable, ask if the user wants to persist it
- Categories: domain, service, pattern, convention, framework, infrastructure, operations, workflow, project, memory
```

### Cursor (`.cursorrules`)

Add this to `.cursorrules` at your project root:

```
# Knowledge Base

You have access to the Knowledge Semantic MCP server for persistent semantic search.

## Available Tools
- knowledge_search(query, category?, limit?) — find relevant knowledge files by semantic similarity
- knowledge_glossary(term?) — look up terms, acronyms, and aliases
- knowledge_write(file_path, content, description, category, glossary_terms?) — create/overwrite + auto-index
- knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms?) — edit + auto-re-index
- knowledge_index(file_path, description, category, glossary_terms?) — index existing file
- knowledge_remove(file_path) — remove from index

## Rules
- Search knowledge before saying "I don't know"
- Use knowledge_glossary for acronyms and terms
- All knowledge writes go through MCP tools, never raw file writes
- When you learn something reusable, offer to persist via knowledge_write
- Categories: domain, service, pattern, convention, framework, infrastructure, operations, workflow, project, memory
```

### Windsurf (`.windsurfrules`)

Add this to `.windsurfrules` at your project root:

```
# Knowledge Base

You have access to the Knowledge Semantic MCP server for persistent semantic search.

## Available Tools
- knowledge_search(query, category?, limit?) — find relevant knowledge files
- knowledge_glossary(term?) — look up terms and aliases
- knowledge_write(file_path, content, description, category, glossary_terms?) — create + auto-index
- knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms?) — edit + auto-re-index
- knowledge_index(file_path, description, category, glossary_terms?) — index existing file
- knowledge_remove(file_path) — remove from index

## Rules
- Search knowledge before saying "I don't know"
- Use knowledge_glossary for acronyms and terms
- All knowledge writes go through MCP tools, never raw file writes
- Offer to persist reusable learnings via knowledge_write
- Categories: domain, service, pattern, convention, framework, infrastructure, operations, workflow, project, memory
```

### GitHub Copilot (`.github/copilot-instructions.md`)

Add this to `.github/copilot-instructions.md` in your repository:

```markdown
# Knowledge Base

You have access to the Knowledge Semantic MCP server for persistent semantic search over project knowledge.

## Available Tools
- `knowledge_search(query, category?, limit?)` — find relevant knowledge files by semantic similarity
- `knowledge_glossary(term?)` — look up terms, acronyms, and aliases
- `knowledge_write(file_path, content, description, category, glossary_terms?)` — create/overwrite + auto-index
- `knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms?)` — edit + auto-re-index
- `knowledge_index(file_path, description, category, glossary_terms?)` — index existing file
- `knowledge_remove(file_path)` — remove from index

## Rules
- Search knowledge before saying "I don't know"
- Use knowledge_glossary for acronyms and terms
- All knowledge writes go through MCP tools, never raw file writes
- Offer to persist reusable learnings via knowledge_write
- Categories: domain, service, pattern, convention, framework, infrastructure, operations, workflow, project, memory
```

## Categories Reference

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

## MCP Server Registration

### Claude Code

```bash
claude mcp add --scope user knowledge-semantic -- python -m knowledge_semantic.mcp_server
```

### Cursor

Open Settings, navigate to MCP Servers, and add a server with the command:

```
python -m knowledge_semantic.mcp_server
```

### Windsurf

Open Settings, navigate to MCP, and add a server with the command:

```
python -m knowledge_semantic.mcp_server
```

### GitHub Copilot

Add to `.github/copilot-mcp.json` in your repository or configure in VS Code settings:

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

Set `KNOWLEDGE_PATH` and `CHROMADB_PATH` environment variables if your knowledge files or ChromaDB data are not at the default locations. You can pass these through your MCP server configuration. For example, in Claude Code:

```bash
claude mcp add --scope user knowledge-semantic -e KNOWLEDGE_PATH=/path/to/knowledge -e CHROMADB_PATH=/path/to/.chromadb -- python -m knowledge_semantic.mcp_server
```
