# Web UI

A local web app for browsing and editing your knowledge base. Optional — install only if you want a graphical front end on top of the MCP server.

## What you get

- **CodeMirror 6 markdown editor** with syntax highlighting and line wrap.
- **Live HTML preview** rendered via markdown-it and sanitized with DOMPurify.
- **Sync scroll** between editor and preview — scroll either side, the other follows in proportion.
- **Collapsible file tree** of `KNOWLEDGE_PATH`, grouped by top-level directory. Toggle the tree with the icon in the top bar.
- **Light / dark theme toggle**, persisted in `localStorage`. Defaults to your OS preference.
- **Auto-save**: 1 second after you stop typing, the file is written and reindexed via the same `KnowledgeStore` the MCP server uses. The index can't drift from disk.

## Install

```bash
pip install -e ".[ui]"
```

The `ui` extra is small — just FastAPI and uvicorn. The MCP-only install path is unaffected.

## Run

```bash
kb-ui
```

First launch triggers a one-time sentence-transformers model download (~80 MB) for embedding new edits — 10-30 seconds. Subsequent launches are instant.

By default it serves at `http://127.0.0.1:7878` and opens your browser. Override:

```bash
KB_UI_HOST=0.0.0.0 KB_UI_PORT=8000 kb-ui
```

## Configuration

The UI honors the same env vars as the MCP server:

| Variable | Default | Purpose |
|---|---|---|
| `KNOWLEDGE_PATH` | `~/knowledge` | Root of your markdown files |
| `CHROMADB_PATH` | `$KNOWLEDGE_PATH/.chromadb` | Where ChromaDB stores its index |
| `KB_UI_HOST` | `127.0.0.1` | UI bind address |
| `KB_UI_PORT` | `7878` | UI port |

## Architecture

```
Browser  ─┐
          ▼
       FastAPI  (knowledge_semantic.ui)
          │
          ├─ /api/tree    → safe filesystem walker
          ├─ /api/file    → read / atomic write + reindex
          └─ /api/status  → indexed count + last_indexed
          │
          ▼
      KnowledgeStore  (knowledge_semantic.store, in-process)
          │
          ▼
       ChromaDB  ($CHROMADB_PATH)
```

The UI imports `KnowledgeStore` directly rather than spawning the MCP server as a subprocess — same write path, in-process, no JSON-RPC overhead. The MCP transport is a thin veneer over the same module.

## Development (frontend changes)

The Svelte source lives at the repo root under `frontend/`. Vite builds into `knowledge_semantic/ui/static/`, which is committed so users without Node can `pip install` and run.

```bash
cd frontend
npm install
npm run build          # one-shot build → ../knowledge_semantic/ui/static
npm run dev            # dev server with HMR + /api proxy to localhost:7878
```

During `npm run dev`, the UI runs on Vite's port (typically 5173) and proxies `/api` and `/healthz` to the FastAPI server at `127.0.0.1:7878`. Start `kb-ui` in another shell first.

## Path safety

`PUT /api/file` rejects any path whose `os.path.realpath` doesn't land under `os.path.realpath(KNOWLEDGE_PATH)`. Both sides are normalized so symlink-laden temp dirs (e.g. macOS `/var/folders` → `/private/var/folders`) compare correctly. Non-`.md` paths are also rejected.

## Concurrent writes with the MCP server

If a Claude Code session is running its MCP-bound writes against the same ChromaDB *while* you're editing in the UI, you may occasionally see `database is locked` — ChromaDB's SQLite serializes writers. The UI absorbs this with a 3-attempt 50 ms-backoff retry. The clean answer if you see frequent contention: don't run both writers simultaneously.

## Sync scroll

Both panes emit a normalized scroll ratio (`scrollTop / (scrollHeight - clientHeight)`) when the user scrolls them. The other pane mirrors that ratio. A one-shot suppression flag absorbs the programmatic scroll event so the mirror doesn't echo back. The mapping is naive — proportional to total height, not aligned to source-line positions — but feels right at typical note lengths.
