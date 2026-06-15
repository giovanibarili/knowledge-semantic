# Knowledge Semantic

Semantic search MCP server for LLM coding agents. Your LLM forgets everything between sessions — this fixes it.

## The Problem

LLM coding agents have no long-term memory. Every session starts from zero — no knowledge of your architecture, conventions, past decisions, or domain vocabulary. The context window is large but ephemeral. When the session ends, everything the agent learned about your system vanishes.

The community response has been to build a brain: structured markdown files that capture what the LLM needs to know. Conventions, service docs, glossaries, project context, runbooks — all curated by hand and fed to the agent through system prompts and config files. This works. You get persistence across sessions, and the LLM stops asking the same questions twice.

But as the brain grows, a new problem emerges: finding the right file. Manual navigation through index files breaks when the wording doesn't match what you're looking for. Search "account authorization" and miss the file titled "auth-service" — because you'd need to already know the mapping. With 50+ files, the LLM spends more time navigating than reasoning.

[mempalace](https://github.com/milla-jovovich/mempalace) opened the door to indexing and semantic retrieval over knowledge files. Knowledge Semantic builds on that foundation — a stripped-down MCP server where the LLM provides all the intelligence and the server handles storage and retrieval through ChromaDB embeddings. The result: your markdown brain becomes searchable by meaning, not just by filename.

## How It Works

Three layers, each with one job:

**MCP Server** — a thin JSON-RPC subprocess that your LLM agent starts automatically. It owns ChromaDB and exposes tools for search, write, and domain management. It stores and retrieves. It never analyzes, summarizes, or decides what matters.

**ChromaDB** — persistent vector database on disk. Each document is one markdown file, identified by its absolute path. Embeddings are computed automatically via Sentence Transformers (`all-MiniLM-L6-v2`). Survives restarts.

**The LLM Client** — the intelligent layer. It reads files, understands their content, defines metadata (description, category, glossary terms), and pushes everything through the MCP tools. The server never decides what's important — the LLM does.

## Tools

### Search tools

**`knowledge_search`** — Semantic search across all indexed files. Returns ranked file paths with similarity scores, metadata, and glossary terms. Supports `domain=` to scope results.

```
knowledge_search(query="deployment runbook") → top 5 files ranked by relevance
knowledge_search(query="authorization flow", domain="deposit-platform") → scoped to domain
```

**`knowledge_hybrid_search`** — Hybrid retrieval: vector (semantic) + BM25 (lexical) fused via Reciprocal Rank Fusion. Best for exact identifiers, acronyms, and kebab-case symbols. Returns `rrf_score`, `vec_rank`, `bm25_rank`, `in_both`, and `glossary_terms`.

```
knowledge_hybrid_search(query=":fixed-income-br tax rule", domain="deposit-platform")
```

**`knowledge_glossary`** — List or search glossary terms across all indexed files. Returns `term`, `aliases`, `definition`, `source_file`, and `domain`.

```
knowledge_glossary(term="SAA") → [{term, aliases, definition, source_file, domain}]
knowledge_glossary()           → all terms across all domains
```

### Write tools

**`knowledge_write`** — Create or overwrite a knowledge file AND auto-index in one atomic call.

```
knowledge_write(file_path, content, description, category, domain?, glossary_terms?)
```

**`knowledge_edit`** — Edit a knowledge file (string replacement) AND auto-re-index.

```
knowledge_edit(file_path, old_string, new_string, description, category, domain?, glossary_terms?)
```

**`knowledge_index`** — Index an existing file without modifying it.

```
knowledge_index(file_path, description, category, domain?, glossary_terms?)
```

**`knowledge_remove`** — Remove a file from the search index.

```
knowledge_remove(file_path)
```

**`knowledge_reindex`** — Bulk re-index a directory of markdown files. Skips files whose mtime is older than their last indexed timestamp. Pass `domain=` to resolve the directory automatically from config.

```
knowledge_reindex(domain="deposit-platform")
knowledge_reindex(directory="/path/to/dir", recursive=True)
```

**`knowledge_status`** — Report index health: total indexed files, stale files (mtime > indexed_at), and orphaned entries (in index but deleted from disk).

```
knowledge_status() → {total_indexed, stale_count, orphaned_count, last_indexed}
```

### Domain tools

**`knowledge_domains`** — List all configured domains with their paths, git URLs, and default flag.

```
knowledge_domains() → [{slug, path, knowledge_path, git_url, is_default}]
```

**`knowledge_pull`** — Run `git pull` on one or all knowledge domains.

```
knowledge_pull(domain="deposit-platform")   ← single domain
knowledge_pull()                            ← all domains
```

**`knowledge_clone`** — Clone a domain's git repository into its configured local path. Skips silently if already cloned.

```
knowledge_clone(domain="gcm")
```

### Why writes go through the MCP

If you edit a knowledge file with a regular text editor and forget to re-index, the search index goes stale. By routing all knowledge writes through `knowledge_write` and `knowledge_edit`, the file mutation and re-indexing happen atomically. One call, always in sync.

## Quick Start

```bash
# Clone
git clone https://github.com/giovanibarili/knowledge-semantic.git
cd knowledge-semantic

# Install
pip install -e ".[dev]"

# Register with Claude Code (user-level, available in all projects)
claude mcp add --scope user knowledge-semantic -- python -m knowledge_semantic.mcp_server
```

For other LLM tools (Cursor, Windsurf, GitHub Copilot), see the [bootstrap guide](docs/llm-bootstrap-guide.md).

### Configuration

The server reads two environment variables:

- `KNOWLEDGE_PATH` — root directory of your knowledge files (default: `~/knowledge`)
- `CHROMADB_PATH` — where ChromaDB stores its data (default: `$KNOWLEDGE_PATH/.chromadb`)

Set them in your MCP server configuration or export them before starting your LLM agent.

### Multi-Domain Configuration

Multiple knowledge bases (domains) are supported. Each domain has its own directory, optional git remote, and scoped search.

Create `~/.jarvis/knowledge-domains.json`:

```json
{
  "default": "personal",
  "domains": {
    "personal": {
      "path": "~/dev/personal/claude-dotfiles",
      "git_url": "https://github.com/yourname/claude-dotfiles.git",
      "git_path": "knowledge"
    },
    "deposit-platform": {
      "path": "~/dev/personal/knowledge-deposit-platform",
      "git_url": "https://github.com/nubank/knowledge-deposit-platform.git",
      "git_path": "."
    },
    "gcm": {
      "path": "~/dev/personal/knowledge-gcm",
      "git_url": "https://github.com/nubank/knowledge-gcm.git",
      "git_path": "."
    }
  }
}
```

Then:

```
knowledge_clone(domain="deposit-platform")
knowledge_reindex(domain="deposit-platform")
knowledge_search(query="SAA authorization", domain="deposit-platform")
```

## Knowledge Structures

Start with 5 files, grow to 100+. The simplest setup is a flat folder:

```
knowledge/
  conventions.md
  glossary.md
  runbook.md
  architecture.md
  .chromadb/
```

As your knowledge base grows, organize by domain — services, patterns, projects. The full progressive guide covers three levels with directory examples and signals for when to scale up.

Full guide: [docs/knowledge-structures.md](docs/knowledge-structures.md)

## Bootstrap Your LLM Agent

Teach your LLM agent to use the knowledge base on every session. The guide explains the generic pattern (what every system prompt needs) and provides copy-paste snippets for Claude Code, Cursor, Windsurf, and GitHub Copilot.

Full guide: [docs/llm-bootstrap-guide.md](docs/llm-bootstrap-guide.md)

## Architecture

```
knowledge_semantic/
├── __init__.py         ← package init, exports version
├── __main__.py         ← entry point: python -m knowledge_semantic.mcp_server
├── version.py          ← single source of truth for version
├── domains.py          ← multi-domain config (Domain, DomainRegistry, git_pull, git_clone)
├── bm25.py             ← BM25 store with lazy rebuild + RRF fusion
├── store.py            ← ChromaDB wrapper (upsert, search, hybrid_search, glossary, remove)
└── mcp_server.py       ← JSON-RPC dispatch + 12 tool handlers

tests/
├── conftest.py         ← fixtures with isolated ChromaDB instances
├── test_store.py       ← store unit tests
├── test_hybrid.py      ← hybrid search + RRF tests
├── test_domains.py     ← domain registry tests
└── test_mcp_server.py  ← MCP protocol and all tool handlers
```

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check knowledge_semantic/ tests/
ruff format --check knowledge_semantic/ tests/
```

114 tests covering all 12 tools, ChromaDB store, hybrid search + RRF fusion, domain registry, MCP protocol dispatch, type coercion, and error paths.

## License

MIT — originally derived from [mempalace](https://github.com/milla-jovovich/mempalace).
