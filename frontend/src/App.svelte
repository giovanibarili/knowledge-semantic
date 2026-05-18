<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import FileTree from "./lib/FileTree.svelte";
  import Editor from "./lib/Editor.svelte";
  import Preview from "./lib/Preview.svelte";
  import StatusBar from "./lib/StatusBar.svelte";
  import { get } from "svelte/store";
  import { getFile, getStatus, getTree, putFile } from "./api";
  import {
    currentFile,
    dirty,
    editorContent,
    saveStatus,
    theme,
    totalIndexed,
    treeOpen,
    treeRoot,
  } from "./stores";

  let mounted = false;
  let saveBtn: HTMLButtonElement;

  $: dirtyValue = $dirty;
  $: saveLabel = $saveStatus === "saving" ? "filing…" : "save to library";

  onMount(async () => {
    mounted = true;
    const [tree, status] = await Promise.all([getTree(), getStatus()]);
    treeRoot.set(tree.root);
    totalIndexed.set(status.total_indexed);

    window.addEventListener("keydown", onKey);
    window.addEventListener("beforeunload", onBeforeUnload);
  });

  onDestroy(() => {
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("beforeunload", onBeforeUnload);
  });

  function onKey(e: KeyboardEvent) {
    const meta = e.metaKey || e.ctrlKey;
    if (meta && e.key.toLowerCase() === "s") {
      e.preventDefault();
      save();
    }
  }

  function onBeforeUnload(e: BeforeUnloadEvent) {
    if (get(dirty)) {
      e.preventDefault();
      e.returnValue = "";
    }
  }

  async function save() {
    const file = get(currentFile);
    if (!file) return;
    if (!get(dirty)) return;
    const content = get(editorContent);
    saveStatus.set("saving");
    try {
      await putFile(file.path, content);
      dirty.set(false);
      saveStatus.set("saved");
      // Refresh status counts so a newly indexed file is reflected.
      const s = await getStatus();
      totalIndexed.set(s.total_indexed);
    } catch (e) {
      console.error(e);
      saveStatus.set("error");
    }
  }

  async function openFile(path: string) {
    if (get(dirty)) {
      const ok = window.confirm("Discard unsaved changes?");
      if (!ok) return;
    }
    const file = await getFile(path);
    currentFile.set(file);
  }

  function toggleTheme() {
    theme.update((t) => (t === "dark" ? "light" : "dark"));
  }
  function toggleTree() {
    treeOpen.update((v) => !v);
  }
</script>

<header class="topbar" class:visible={mounted}>
  <button class="icon left" on:click={toggleTree} aria-label="Toggle file tree">
    {#if $treeOpen}
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <rect x="1.5" y="2.5" width="13" height="11" rx="0.5" fill="none" stroke="currentColor" />
        <line x1="6" y1="2.5" x2="6" y2="13.5" stroke="currentColor" />
      </svg>
    {:else}
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <rect x="1.5" y="2.5" width="13" height="11" rx="0.5" fill="none" stroke="currentColor" />
      </svg>
    {/if}
  </button>

  <h1 class="brand">
    <span class="brand-name">Knowledge</span>
    <span class="brand-flourish">❦</span>
  </h1>

  <div class="actions">
    <button
      class="save"
      bind:this={saveBtn}
      class:active={dirtyValue}
      class:saving={$saveStatus === "saving"}
      on:click={save}
      disabled={!$currentFile || (!dirtyValue && $saveStatus !== "error")}
      title="Save & index (⌘S)"
    >
      <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
        <path
          d="M3 2 h8 l2 2 v10 H3 Z"
          fill="none"
          stroke="currentColor"
          stroke-linejoin="miter"
        />
        <line x1="5" y1="2" x2="5" y2="6" stroke="currentColor" />
        <line x1="10" y1="2" x2="10" y2="6" stroke="currentColor" />
        <line x1="5" y1="9" x2="11" y2="9" stroke="currentColor" />
        <line x1="5" y1="11.5" x2="11" y2="11.5" stroke="currentColor" />
      </svg>
      <span>{saveLabel}</span>
      <kbd>⌘S</kbd>
    </button>

    <button class="icon right" on:click={toggleTheme} aria-label="Toggle theme">
      {#if $theme === "dark"}
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <circle cx="8" cy="8" r="3" fill="currentColor" />
          <g stroke="currentColor" stroke-linecap="round">
            <line x1="8" y1="1" x2="8" y2="3" />
            <line x1="8" y1="13" x2="8" y2="15" />
            <line x1="1" y1="8" x2="3" y2="8" />
            <line x1="13" y1="8" x2="15" y2="8" />
            <line x1="3" y1="3" x2="4.5" y2="4.5" />
            <line x1="11.5" y1="11.5" x2="13" y2="13" />
            <line x1="13" y1="3" x2="11.5" y2="4.5" />
            <line x1="4.5" y1="11.5" x2="3" y2="13" />
          </g>
        </svg>
      {:else}
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path
            d="M13.5 9.5 A6 6 0 1 1 6.5 2.5 A5 5 0 0 0 13.5 9.5 Z"
            fill="currentColor"
          />
        </svg>
      {/if}
    </button>
  </div>
</header>

<main class="app" class:tree-closed={!$treeOpen} class:visible={mounted}>
  {#if $treeOpen}
    <aside class="tree-pane">
      {#if $treeRoot}
        <FileTree node={$treeRoot} {openFile} />
      {:else}
        <p class="loading"><em>loading…</em></p>
      {/if}
    </aside>
  {/if}

  <section class="editor-pane"><Editor /></section>
  <section class="preview-pane"><Preview /></section>
</main>

<StatusBar />

<style>
  :global(:root) {
    /* parchment palette — light theme */
    --bg: #f6f1e7;
    --bg-elev: #fbf8f1;
    --bg-sunken: #ede4d2;
    --fg: #2c2418;
    --fg-muted: #7d6f57;
    --border: #d4c8b0;
    --rule: #a89878;
    --accent: #7a2e1f;
    --accent-soft: #7a2e1f1a;
    --status-ok: #4a6741;
    --status-warn: #8a5a1a;
    --status-err: #8a2a2a;

    --font-serif:
      "Fraunces", "Source Serif 4", Georgia, "Iowan Old Style", serif;
    --font-mono:
      "JetBrains Mono", "Berkeley Mono", "IBM Plex Mono", ui-monospace, Menlo, monospace;
  }
  :global(:root[data-theme="dark"]) {
    /* lamp-lit reading — dark theme */
    --bg: #1c1813;
    --bg-elev: #221d16;
    --bg-sunken: #15110c;
    --fg: #e8dcc0;
    --fg-muted: #9a8d75;
    --border: #3a3025;
    --rule: #5a4a35;
    --accent: #d4a574;
    --accent-soft: #d4a5741a;
    --status-ok: #a8c192;
    --status-warn: #e5b870;
    --status-err: #e09090;
  }
  :global(html, body, #app) {
    height: 100%;
  }
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: var(--font-serif);
    font-size: 14px;
    font-feature-settings: "ss01", "ss02", "kern";
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    background-image: radial-gradient(
      ellipse at 30% 20%,
      transparent 0%,
      var(--accent-soft) 100%
    );
    background-attachment: fixed;
  }
  :global(#app) {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: 100vh;
  }
  .topbar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 16px;
    padding: 16px 24px 14px;
    background: var(--bg-elev);
    border-bottom: 1px solid var(--rule);
    position: relative;
    opacity: 0;
    transform: translateY(-4px);
    transition:
      opacity 600ms ease-out,
      transform 600ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  .topbar::after {
    content: "";
    position: absolute;
    left: 24px;
    right: 24px;
    bottom: -4px;
    height: 1px;
    background: var(--rule);
    opacity: 0.35;
  }
  .topbar.visible {
    opacity: 1;
    transform: translateY(0);
  }
  .brand {
    margin: 0;
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 144, "wght" 400, "SOFT" 0, "WONK" 1;
    font-size: 22px;
    line-height: 1;
    color: var(--fg);
    letter-spacing: -0.01em;
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
  }
  .brand-name {
    font-style: italic;
  }
  .brand-flourish {
    font-size: 14px;
    color: var(--accent);
    transform: translateY(-1px);
  }
  .actions {
    grid-column: 3;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .icon {
    background: none;
    border: 1px solid var(--border);
    color: var(--fg-muted);
    cursor: pointer;
    padding: 5px 7px;
    border-radius: 1px;
    line-height: 0;
    transition:
      color 180ms ease,
      border-color 180ms ease,
      background 180ms ease;
  }
  .icon:hover {
    color: var(--accent);
    border-color: var(--accent);
    background: var(--accent-soft);
  }

  /* Save button — feature-prominent, library binding feel */
  .save {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-sunken);
    border: 1px solid var(--border);
    border-radius: 1px;
    padding: 4px 10px 4px 9px;
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 14, "wght" 500;
    font-variant: small-caps;
    letter-spacing: 0.08em;
    font-size: 12px;
    color: var(--fg-muted);
    cursor: pointer;
    transition:
      color 180ms ease,
      border-color 180ms ease,
      background 220ms ease,
      transform 120ms ease;
  }
  .save:disabled {
    cursor: default;
    opacity: 0.55;
  }
  .save:not(:disabled):hover {
    color: var(--accent);
    border-color: var(--accent);
  }
  .save:not(:disabled):active {
    transform: translateY(1px);
  }
  .save.active {
    color: var(--accent);
    border-color: var(--accent);
    background: var(--accent-soft);
    animation: save-pulse 1.8s ease-in-out infinite;
  }
  .save.saving {
    color: var(--status-warn);
    border-color: var(--status-warn);
    background: var(--bg-sunken);
    animation: none;
  }
  .save kbd {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--fg-muted);
    background: transparent;
    border: 1px solid var(--border);
    padding: 1px 4px;
    border-radius: 1px;
    letter-spacing: 0;
    text-transform: none;
    font-variant: normal;
    margin-left: 2px;
  }
  .save.active kbd {
    border-color: var(--accent);
    color: var(--accent);
  }
  @keyframes save-pulse {
    0%, 100% {
      box-shadow: 0 0 0 0 var(--accent-soft);
    }
    50% {
      box-shadow: 0 0 0 4px var(--accent-soft);
    }
  }

  .app {
    display: grid;
    grid-template-columns: 220px 1fr 1fr;
    min-height: 0;
    opacity: 0;
    transition: opacity 700ms ease-out 120ms;
  }
  .app.visible {
    opacity: 1;
  }
  .app.tree-closed {
    grid-template-columns: 1fr 1fr;
  }
  .tree-pane {
    background: var(--bg-elev);
    border-right: 1px solid var(--rule);
    overflow: auto;
    padding: 18px 18px 18px 22px;
  }
  .editor-pane,
  .preview-pane {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }
  .editor-pane {
    border-right: 1px solid var(--rule);
    background: var(--bg-sunken);
  }
  .preview-pane {
    background: var(--bg);
  }
  .loading {
    color: var(--fg-muted);
    font-style: italic;
    font-family: var(--font-serif);
  }
</style>
