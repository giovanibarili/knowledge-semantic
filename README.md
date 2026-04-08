# Knowledge Semantic

Semantic search MCP server for curated knowledge files. The LLM client provides all intelligence — the server is dumb storage and retrieval over ChromaDB.

Fork of [mempalace](https://github.com/milla-jovovich/mempalace), stripped to the essentials.

## The Problem

A knowledge base of 100+ markdown files is only useful if you can find what you need. Manual navigation through index files breaks when the wording doesn't match what you're looking for. Search "account authorization" and miss the file titled "SAA" — because you'd need to already know that SAA *is* the authorization engine.

Semantic search fixes this. The embeddings understand that "account authorization" and "SAA" live in the same neighborhood, regardless of exact wording.

## How It Works

Three layers, each with one job:

**MCP Server** — a thin JSON-RPC subprocess that Claude Code starts automatically. It owns ChromaDB and exposes 6 tools. It stores and retrieves. It never analyzes, summarizes, or decides what matters.

**ChromaDB** — persistent vector database on disk. Each document is one markdown file, identified by its absolute path. Embeddings are computed automatically via Sentence Transformers (`all-MiniLM-L6-v2`). Survives restarts.

**The LLM Client** — the intelligent layer. It reads files, understands their content, defines metadata (description, category, glossary terms), and pushes everything through the MCP tools. The server never decides what's important — the LLM does.

## Tools

### Read tools

**`knowledge_search`** — Semantic search across all indexed files. Returns ranked file paths with similarity scores and metadata. The LLM then uses `Read` on the paths it needs.

```
knowledge_search(query="account authorization") → top 5 files ranked by relevance
```

**`knowledge_glossary`** — List or search glossary terms across all indexed files. Case-insensitive substring match against terms and aliases.

```
knowledge_glossary(term="SAA") → [{term, aliases, definition, source_file}]
knowledge_glossary()           → all 500+ terms
```

### Write tools

**`knowledge_index`** — Push an existing file into ChromaDB with LLM-defined metadata. Reads the file from disk, computes the embedding, stores with description, category, and glossary terms. Updates in place if already indexed.

```
knowledge_index(file_path, description, category, glossary_terms)
```

**`knowledge_write`** — Create or overwrite a knowledge file AND auto-index in one atomic call. The file is written to disk and indexed in ChromaDB in a single operation — the index can never go stale.

```
knowledge_write(file_path, content, description, category, glossary_terms)
```

**`knowledge_edit`** — Edit a knowledge file (string replacement) AND auto-re-index. Replaces the first occurrence of `old_string` with `new_string`, writes back, re-indexes. One call, both the file and the index stay in sync.

```
knowledge_edit(file_path, old_string, new_string, description, category, glossary_terms)
```

**`knowledge_remove`** — Remove a file from the search index.

```
knowledge_remove(file_path)
```

### Why write and edit go through the MCP

If you edit a knowledge file with a regular text editor and forget to re-index, the search index goes stale. By routing all knowledge writes through `knowledge_write` and `knowledge_edit`, the file mutation and re-indexing happen atomically. One call, always in sync.

## Installation

```bash
# Clone
git clone https://github.com/giovanibarili/knowledge-semantic.git
cd knowledge-semantic

# Install (use public PyPI — internal registries may not have chromadb)
pip install -e ".[dev]" --index-url https://pypi.org/simple/

# Register with Claude Code (user-level, available in all projects)
claude mcp add --scope user knowledge-semantic -- python -m knowledge_semantic.mcp_server
```

### Configuration

The server reads two environment variables:

- `KNOWLEDGE_PATH` — root directory of your knowledge files (default: `~/dev/personal/claude-dotfiles/knowledge`)
- `CHROMADB_PATH` — where ChromaDB stores its data (default: `~/dev/personal/claude-dotfiles/knowledge/.chromadb`)

To override, set them in the MCP server configuration or export them before starting Claude Code.

## Onboarding: Building Your Knowledge Base

The server starts empty. The LLM client builds the knowledge base by pushing files one at a time with structured metadata. Here's the onboarding flow.

### Step 1: Create your knowledge directory

```
~/your-knowledge/
├── index.md              ← navigation map (optional but recommended)
├── services/
│   ├── auth-service.md
│   └── payment-service.md
├── patterns/
│   └── retry-pattern.md
└── .chromadb/            ← auto-created by the server
```

### Step 2: Index existing files

Tell the LLM: *"Index the knowledge base."*

The LLM reads each markdown file, analyzes its content, and calls `knowledge_index` with:
- **file_path** — absolute path to the file
- **description** — one-line summary of what the file contains
- **category** — one of: `domain`, `service`, `pattern`, `convention`, `framework`, `infrastructure`, `operations`, `workflow`, `claude-code`, `project`, `memory`
- **glossary_terms** — key terms found in the file, each with term name, aliases, and definition

The LLM provides the intelligence. It decides what the description should be, which category fits, and which terms to extract. The server just stores the embeddings and metadata.

### Step 3: Use it

Once indexed, the LLM can search semantically:

```
User: "How does settlement work?"

LLM calls: knowledge_search("settlement")
LLM gets:  5 ranked files — sa-authorizer-adapter.md, fix-yield-crash/checkpoint.md, ...
LLM calls: Read("sa-authorizer-adapter.md")
LLM reads: the actual file content
LLM answers: based on real knowledge, not hallucination
```

### Step 4: Keep it in sync

When creating new knowledge files, the LLM uses `knowledge_write` instead of writing directly. When editing, it uses `knowledge_edit`. Both write the file to disk AND update the index in one call.

```
LLM learns something new about auth-service
LLM calls: knowledge_edit(
    file_path="auth-service.md",
    old_string="uses JWT tokens",
    new_string="uses JWT tokens with 24h expiry and HttpOnly refresh cookies",
    description="Auth service overview with token details",
    category="service",
    glossary_terms=[...]
)
→ File updated on disk AND search index updated atomically
```

## Claude Code Bootstrap Integration

For Claude Code users with a `CLAUDE.md` configuration, the knowledge-semantic MCP server integrates into the session bootstrap:

### On session start

1. Claude Code starts the MCP server as a subprocess (configured via `claude mcp add`)
2. ChromaDB loads the persisted data from `.chromadb/` — search works immediately
3. The LLM can use `knowledge_search` to find relevant knowledge instead of navigating index files manually

### During the session

- **Finding knowledge:** `knowledge_search("topic")` replaces manual index navigation
- **Creating knowledge:** `knowledge_write(path, content, ...)` replaces `Write` + manual `knowledge_index`
- **Editing knowledge:** `knowledge_edit(path, old, new, ...)` replaces `Edit` + manual `knowledge_index`
- **Looking up terms:** `knowledge_glossary("term")` replaces reading glossary files

### On a fresh machine

1. Clone your dotfiles repo (gets `knowledge/` files + `.chromadb/` if tracked, or `.gitignore`d)
2. Install knowledge-semantic: `pip install -e /path/to/knowledge-semantic`
3. MCP config is already in Claude Code settings → server starts automatically
4. If `.chromadb/` was gitignored, tell the LLM: *"Index the knowledge base"* — one-time bootstrap, takes a few minutes for ~150 files

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check knowledge_semantic/ tests/
ruff format --check knowledge_semantic/ tests/
```

32 tests covering all 6 tools, the ChromaDB store, MCP protocol dispatch, type coercion, and error paths.

## Architecture

```
knowledge_semantic/
├── __init__.py         ← package init, exports version
├── __main__.py         ← entry point: python -m knowledge_semantic.mcp_server
├── version.py          ← single source of truth for version
├── store.py            ← ChromaDB wrapper (upsert, search, glossary, remove)
└── mcp_server.py       ← JSON-RPC dispatch + 6 tool handlers

tests/
├── conftest.py         ← fixtures with isolated ChromaDB instances
├── test_store.py       ← 13 tests for the store module
└── test_mcp_server.py  ← 19 tests for MCP protocol and tools
```

## License

MIT — inherited from [mempalace](https://github.com/milla-jovovich/mempalace).
