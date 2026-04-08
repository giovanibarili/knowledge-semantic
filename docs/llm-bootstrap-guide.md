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

## Making Knowledge Your Default Workflow

The tools and rules above tell you *what* is available. This section tells you *how* to weave the knowledge base into your daily workflow so it becomes your default way of operating — not an afterthought.

The pattern below has been refined over months of daily use. It turns the knowledge base into a genuine second brain: the LLM knows what it knows, recovers context between sessions, learns from corrections, and grows the knowledge organically as work happens.

### Session Bootstrap

At the beginning of every new conversation, load your context from the knowledge base before doing anything else.

1. Query `knowledge_search` for active projects and their current state.
2. For each active project, check if a checkpoint file exists (e.g., `projects/<project>/checkpoint.md`). If it does, read it — this is the recovery point from the last session. It tells you what was being done, where it stopped, and what comes next.
3. Present the user with a brief status: active projects, their state, and what's ready to resume.

This means every session starts with context, not from zero. The user never has to re-explain what they were working on.

Add this to your configuration file:

```markdown
## Bootstrap — Session Start

At the beginning of every conversation:

1. Use `knowledge_search("active projects", category="project")` to find current work.
2. For each active project, read its checkpoint file if one exists.
3. Present a brief status summary before asking what to work on.
```

### Proactive Knowledge Persistence

Do not wait for the user to ask you to save knowledge. When you learn something reusable during a session — a pattern, a convention, a decision rationale, a term definition — offer to persist it. The knowledge base only grows if you actively feed it.

Conversely, when the user corrects you or confirms a non-obvious approach, that is knowledge worth capturing. "Always use feature flags for behavior changes" or "never mock the database in integration tests" — these are learnings that should survive the session.

Add this to your configuration file:

```markdown
## Knowledge Persistence

- When you learn something reusable, ask the user if they want to persist it via `knowledge_write`.
- When the user corrects your approach or confirms a non-obvious choice, offer to save it as a convention or feedback note.
- When the user shares links, commands, or references, persist them to the active project's knowledge folder.
```

### Session Checkpoints

When the user ends a session, write a checkpoint for each active project before shutting down. The checkpoint is a full brain dump — everything needed to resume the exact mental state of the session.

A good checkpoint includes: what you were doing, where you stopped, decisions made and why, open questions, blockers, and what comes next. Overwrite the previous checkpoint — only the latest matters.

Add this to your configuration file:

```markdown
## Session Checkpoints

When the user ends the session, persist a checkpoint for each active project:

- File: `knowledge/projects/<project>/checkpoint.md`
- Content: what we were doing, where we stopped, decisions made, open questions, next steps
- Use `knowledge_write` to save and index the checkpoint
- Overwrite previous checkpoint — only the latest matters
```

### Knowledge-First Lookup

Make the knowledge base your first stop for any question about the project, domain, or conventions. Before reading code, before searching the web, before guessing — check the knowledge base. Someone (possibly you, in a previous session) may have already documented the answer.

Add this to your configuration file:

```markdown
## Knowledge-First Lookup

- Always consult knowledge before saying "I don't know": `knowledge_glossary` for terms, `knowledge_search` for content.
- Read the returned file paths for full content — search results are pointers, not answers.
- If the knowledge base has no answer, then proceed with other approaches.
```

### Project Lifecycle

Active projects live in `knowledge/projects/<name>/`. Each project folder holds its own context: README, checkpoint, decisions, links, runbooks. When a project is done, review its contents with the user — anything worth preserving long-term (patterns, lessons learned, reusable playbooks) gets promoted to the top-level knowledge directories. Then delete the project folder.

This keeps the knowledge base clean: projects are ephemeral workspaces, while conventions, patterns, and services are long-lived reference material.

### Example Configuration Block

Here is a complete example combining all the patterns above. Adapt it to your tool's configuration format:

```markdown
## Knowledge Base

The Knowledge Semantic MCP server provides persistent semantic search over your knowledge files.

### MCP Tools
- `knowledge_search(query, category?, limit?)` — semantic search. Returns ranked paths. Read them for content.
- `knowledge_glossary(term?)` — look up terms and aliases.
- `knowledge_write(file_path, content, description, category, glossary_terms?)` — create/overwrite + auto-index.
- `knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms?)` — edit + auto-re-index.
- `knowledge_index(file_path, description, category, glossary_terms?)` — index existing file.
- `knowledge_remove(file_path)` — remove from index.

### Rules
- Always search before saying "I don't know."
- All knowledge writes go through MCP tools — never raw file operations.
- Proactively persist reusable learnings, corrections, and non-obvious decisions.
- Include glossary_terms for key terminology when indexing.
- Categories: domain, service, pattern, convention, framework, infrastructure, operations, workflow, project, memory.

### Session Bootstrap
At the start of every conversation:
1. Search for active projects via `knowledge_search`.
2. Read checkpoint files for each active project.
3. Present status before asking what to work on.

### Session Checkpoints
When the session ends:
1. Write a checkpoint for each active project via `knowledge_write`.
2. Include: what we were doing, where we stopped, decisions, next steps.
3. Overwrite previous checkpoint.

### Knowledge Lifecycle
- Projects live in `projects/<name>/` — ephemeral, delete when done.
- Promote reusable knowledge to top-level directories before deleting a project.
- Conventions, patterns, and services are long-lived — projects are not.
```

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
