<script lang="ts">
  import { onMount } from "svelte";
  import FileTree from "./lib/FileTree.svelte";
  import Editor from "./lib/Editor.svelte";
  import Preview from "./lib/Preview.svelte";
  import StatusBar from "./lib/StatusBar.svelte";
  import { getStatus, getTree } from "./api";
  import { theme, totalIndexed, treeOpen, treeRoot } from "./stores";

  onMount(async () => {
    const [tree, status] = await Promise.all([getTree(), getStatus()]);
    treeRoot.set(tree.root);
    totalIndexed.set(status.total_indexed);
  });

  function toggleTheme() {
    theme.update((t) => (t === "dark" ? "light" : "dark"));
  }
  function toggleTree() {
    treeOpen.update((v) => !v);
  }
</script>

<header class="topbar">
  <button class="icon" on:click={toggleTree} title="Toggle file tree" aria-label="Toggle file tree">
    {$treeOpen ? "◧" : "◨"}
  </button>
  <strong class="brand">Knowledge</strong>
  <span class="spacer"></span>
  <button class="icon" on:click={toggleTheme} title="Toggle theme" aria-label="Toggle theme">
    {$theme === "dark" ? "☀" : "☾"}
  </button>
</header>

<main class="app" class:tree-closed={!$treeOpen}>
  {#if $treeOpen}
    <aside class="tree-pane">
      {#if $treeRoot}
        <FileTree node={$treeRoot} />
      {:else}
        <p class="loading">loading…</p>
      {/if}
    </aside>
  {/if}

  <section class="editor-pane"><Editor /></section>
  <section class="preview-pane"><Preview /></section>
</main>

<StatusBar />

<style>
  :global(:root) {
    --bg: #ffffff;
    --bg-elev: #fafafa;
    --bg-sunken: #f4f4f5;
    --fg: #1f2328;
    --fg-muted: #6b7280;
    --border: #e5e7eb;
    --accent: #4f46e5;
    --status-ok: #15803d;
    --status-warn: #b45309;
    --status-err: #b91c1c;
  }
  :global(:root[data-theme="dark"]) {
    --bg: #15181d;
    --bg-elev: #1a1d22;
    --bg-sunken: #0f1115;
    --fg: #e5e8eb;
    --fg-muted: #8b939c;
    --border: #2a2f36;
    --accent: #8ab4ff;
    --status-ok: #7be3a5;
    --status-warn: #ffb86b;
    --status-err: #ff7b9c;
  }
  :global(html, body, #app) {
    height: 100%;
  }
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--fg);
    font-family:
      ui-sans-serif,
      -apple-system,
      "Segoe UI",
      sans-serif;
    font-size: 13px;
  }
  #app {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: 100vh;
  }
  .topbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: var(--bg-elev);
    border-bottom: 1px solid var(--border);
  }
  .brand {
    font-size: 13px;
    letter-spacing: 0.04em;
  }
  .spacer {
    flex: 1;
  }
  .icon {
    background: none;
    border: 1px solid var(--border);
    color: var(--fg);
    cursor: pointer;
    padding: 2px 8px;
    font-size: 14px;
    line-height: 1.4;
    border-radius: 4px;
  }
  .icon:hover {
    background: var(--bg-sunken);
  }
  .app {
    display: grid;
    grid-template-columns: 240px 1fr 1fr;
    min-height: 0;
  }
  .app.tree-closed {
    grid-template-columns: 1fr 1fr;
  }
  .tree-pane {
    background: var(--bg-elev);
    border-right: 1px solid var(--border);
    overflow: auto;
    padding: 0.5rem 0.75rem;
  }
  .editor-pane,
  .preview-pane {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }
  .editor-pane {
    border-right: 1px solid var(--border);
  }
  .loading {
    color: var(--fg-muted);
    font-style: italic;
  }
</style>
