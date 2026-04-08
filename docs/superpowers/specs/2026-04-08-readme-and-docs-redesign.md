# Spec: README and Docs Redesign

**Date:** 2026-04-08
**Status:** Approved
**Codename:** Knowledge Semantic Docs Refresh

## Goal

Transform the knowledge-semantic repo from a personal tool with Nubank-specific references into a polished open-source project for any LLM coding agent that supports MCP. Deliver three artifacts: a rewritten README, a progressive knowledge structures guide, and an LLM bootstrap guide with per-tool snippets.

## Audience

Any developer using an LLM coding agent (Claude Code, Cursor, Windsurf, GitHub Copilot, etc.) who wants persistent semantic memory across sessions. No assumed familiarity with any specific company, codebase, or toolchain.

## Deliverables

### 1. README.md (rewrite)

**Hero section** — One-line pitch + the problem/solution in 2 short paragraphs. Hook: "your LLM forgets everything between sessions — this fixes it." No fork mention at the top (attribution in footer).

**How It Works** — Three layers (MCP Server, ChromaDB, LLM Client) with generic language. "Your LLM agent" instead of "Claude Code." Push-model explanation: LLM provides intelligence, server is dumb storage.

**Tools** — Keep the 6-tool reference. Generalize examples (replace domain-specific terms like "SAA" with universal examples like "auth-service", "deployment runbook"). Keep the code block format — it's the best part of the current README.

**Quick Start** — Install + register MCP in 4 commands. `claude mcp add` as one example, with note: "see the bootstrap guide for other tools."

**Knowledge Structures teaser** — Short paragraph + inline starter example (3-4 files) as teaser. Link to `docs/knowledge-structures.md`.

**Bootstrap Guide teaser** — Short paragraph + link to `docs/llm-bootstrap-guide.md`. One sentence: "teach your LLM agent to use the knowledge base on every session."

**Architecture** — Keep current section, clean internal references.

**Development** — Keep current section (pytest, ruff).

**License** — MIT with mempalace attribution.

### 2. docs/knowledge-structures.md

Progressive guide with three levels. Each level includes a complete directory tree example and a "when to level up" section.

**Starter (5-10 files)** — Flat folder with the essentials: project conventions, runbooks, basic glossary. Target: solo dev who wants the LLM to remember project rules.

Example tree:
```
knowledge/
  conventions.md
  glossary.md
  runbook.md
  architecture.md
  .chromadb/
```

**Intermediate (20-50 files)** — Organized by domain: `services/`, `conventions/`, `patterns/`, `projects/`. Glossary distributed across files via metadata. Target: dev working across multiple services/projects who needs cross-cutting context.

Example tree:
```
knowledge/
  index.md
  services/
    auth-service.md
    payment-service.md
    notification-service.md
  conventions/
    code-style.md
    testing-strategy.md
    git-workflow.md
  patterns/
    retry-pattern.md
    circuit-breaker.md
  projects/
    feature-x/
      README.md
      decisions.md
  .chromadb/
```

**Advanced (100+ files)** — Everything from intermediate + `projects/` with checkpoints per project, `memory/` for persistent preferences and feedback, index files for human navigation. Target: power user who uses the LLM as a daily pair programmer with session continuity.

Example tree:
```
knowledge/
  index.md
  domain/
    glossary/
      index.md
    business-rules.md
  services/
    auth-service.md
    payment-service.md
  conventions/
    code-style.md
    testing-strategy.md
    architecture-guidelines.md
  patterns/
    retry-pattern.md
    circuit-breaker.md
    saga-pattern.md
  projects/
    feature-x/
      README.md
      checkpoint.md
      decisions.md
      links.md
    feature-y/
      README.md
      checkpoint.md
  memory/
    user-preferences.md
    feedback-log.md
  .chromadb/
```

Each level ends with "When to level up" — signals that the current structure isn't enough (e.g., "you keep creating files that don't fit any existing folder", "you lose track of what you decided last week on project X").

### 3. docs/llm-bootstrap-guide.md

**The generic pattern** — Explains the concept: your LLM agent needs system prompt instructions to know the knowledge base exists and how to use it. Three blocks every system prompt needs:

1. Where the knowledge lives (path + MCP server name)
2. Which tools to use and when (search before saying "I don't know", write/edit through MCP to keep index in sync)
3. How to maintain the index (use knowledge_write/knowledge_edit, not raw file writes)

**Per-tool snippets** — Copy-paste examples for:

- **Claude Code** (`CLAUDE.md`) — knowledge rules section with MCP tool references
- **Cursor** (`.cursorrules`) — equivalent rules adapted to Cursor's format
- **Windsurf** (`.windsurfrules`) — equivalent rules adapted to Windsurf's format
- **GitHub Copilot** (`.github/copilot-instructions.md`) — equivalent rules adapted to Copilot's format

Each snippet is self-contained: copy, paste into the config file, and the agent knows how to use the knowledge base.

**Bootstrap flow** — Simple explanation of first session vs subsequent sessions:
- First session: "Index the knowledge base" → LLM reads all files, calls knowledge_index for each
- Subsequent sessions: ChromaDB loads from disk, search works immediately, no re-indexing needed

**Categories reference** — List the available categories with one-line descriptions: domain, service, pattern, convention, framework, infrastructure, operations, workflow, project, memory. Generic enough for any codebase.

## What to remove from the current README

- All references to Nubank, SAA, dotfiles, Nu CLI
- Fork/mempalace mention from the top (move to footer attribution)
- Internal PyPI registry note ("use public PyPI")
- Specific file paths like `~/dev/personal/claude-dotfiles/knowledge`
- Domain-specific examples in tool usage

## What to keep

- The 3-layer architecture explanation (MCP Server / ChromaDB / LLM Client)
- The 6 tools reference with code blocks
- The "why writes go through MCP" explanation
- Architecture section (source file listing)
- Development section (pytest, ruff)
- The push-model philosophy (LLM provides intelligence)

## Out of scope

- Code changes to the MCP server itself
- New features or tools
- ChromaDB cosine similarity fix (separate task)
- Re-indexing or data migration
