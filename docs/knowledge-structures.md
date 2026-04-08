# Knowledge Structures Guide

Your knowledge base can start with 5 files and grow to 100+. This guide shows three levels of organization, each building on the previous. Pick the level that matches your current needs and grow into the next one when you feel the friction.

## Starter (5-10 files)

Best for a solo developer who wants their LLM coding agent to remember project rules, coding standards, and common procedures. No subdirectories needed — a flat folder gets the job done.

```
knowledge/
  conventions.md
  glossary.md
  runbook.md
  architecture.md
  .chromadb/
```

**conventions.md** holds your coding standards, PR review rules, git branching strategy, and any "always do X, never do Y" rules you want the LLM to follow. Think of it as the single source of truth for how code should look and flow in your project.

**glossary.md** defines key terms, acronyms, and domain-specific vocabulary. When the LLM encounters "DLQ" or "saga" in your codebase, this file tells it what those mean in your context.

**runbook.md** collects common commands and procedures — how to run tests, deploy, check logs, restart services. Anything you'd otherwise have to type out or search your shell history for.

**architecture.md** gives the LLM a high-level view of your system: what services exist, how they communicate, and the key technical decisions behind the design.

**.chromadb/** is created automatically by the server. It stores the vector embeddings that power semantic search. You never need to touch this directory, but don't delete it — it's your search index.

### When to level up

You've outgrown the starter structure when you notice these signals:

- You have multiple services and one `conventions.md` doesn't cut it anymore. Auth has different testing rules than payments, and they keep clashing in the same file.
- You scroll past paragraphs of unrelated content to find the one section you need.
- You start prefixing filenames like `conventions-auth.md`, `conventions-payments.md` — that's your brain asking for subdirectories.

## Intermediate (20-50 files)

Best for a developer working across multiple services or projects who needs cross-cutting context. Files are organized by domain into subdirectories, and an index file ties everything together.

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

**index.md** is a human-readable navigation map that links to every file in the knowledge base. It's optional — semantic search works perfectly without it — but it helps when you want to browse the knowledge base yourself or give a new team member an overview of what's documented.

At this level, there's no need for a separate glossary file. Each knowledge file declares its own terms through the `glossary_terms` parameter when you index it. The server consolidates these terms automatically, so searching for "DLQ" finds the right file whether the term was defined in `services/notification-service.md` or `patterns/retry-pattern.md`.

The `projects/` directory is where you track active work. Each project gets a folder with a README describing the goal and a decisions file capturing the "why" behind architectural choices. When a project is done, you can delete its folder — the reusable knowledge should already live in `services/`, `conventions/`, or `patterns/`.

### When to level up

You've outgrown the intermediate structure when:

- You lose track of what you decided last week on project X because the context is scattered across conversation history that the LLM can't access.
- You want the LLM to remember your preferences across sessions — how you like commit messages, what review style you prefer, which trade-offs you consistently make.
- Projects accumulate enough context that they need their own checkpoint files so you can resume exactly where you left off.

## Advanced (100+ files)

Best for a power user who treats the LLM as a daily pair programmer and needs session continuity, persistent preferences, and rich project context.

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

Three new concepts appear at this level: checkpoints, memory, and a consolidated domain glossary.

**Checkpoints** (`projects/*/checkpoint.md`) are session recovery points. When you end a work session, the LLM writes down what you were doing, where you stopped, what's next, and any open questions. When you start the next session, it reads the checkpoint and resumes with full context. No more "where were we?" — the LLM picks up exactly where it left off.

**Memory** (`memory/`) stores information that persists across all projects and sessions. `user-preferences.md` captures how you like to work: your preferred commit message style, whether you want verbose or terse explanations, which patterns you favor. `feedback-log.md` records corrections and confirmations from past sessions so the LLM learns from its mistakes without repeating them.

**Domain glossary** (`domain/glossary/index.md`) is a consolidated, human-browsable view of all terms across your knowledge base. While the server can find terms via semantic search regardless of where they're defined, a single glossary file is useful when onboarding someone or when you want to review all domain terminology in one place.

Not all directories have the same lifespan. `projects/` folders are ephemeral — create them when work starts, delete them when it's done (after promoting any reusable knowledge to the appropriate top-level directory). `memory/` and `conventions/` are long-lived — they grow over time and rarely lose content. `services/` and `patterns/` sit in between, evolving as your system architecture changes.

## Tips

**Start small.** Don't create the advanced structure on day one. Begin with the starter layout and let complexity emerge from real needs, not hypothetical ones.

**Let it grow organically.** Create files as you need them, not preemptively. An empty `patterns/` directory with a single placeholder file helps no one. Wait until you actually document a retry pattern, then create the directory.

**The LLM is your librarian.** Semantic search means you don't need perfect organization for the LLM to find things. But good organization helps both you and the LLM. The LLM finds content faster when files are focused on a single topic, and you find content faster when the directory structure mirrors how you think about your system.

**Categories matter for filtering.** Use consistent categories when indexing files — `domain`, `service`, `pattern`, `convention`, `project`, `memory`, and so on. The `knowledge_search` tool can filter by category, so tagging a file as `convention` means you can later search "testing rules" scoped to conventions only, skipping unrelated matches in service docs or project notes.
