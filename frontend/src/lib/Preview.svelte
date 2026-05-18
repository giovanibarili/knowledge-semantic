<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import MarkdownIt from "markdown-it";
  import anchor from "markdown-it-anchor";
  import DOMPurify from "dompurify";
  import { editorContent, currentFile, syncScroll } from "../stores";

  const md = new MarkdownIt({ html: false, linkify: true, breaks: false }).use(anchor);

  let host: HTMLDivElement;
  let rendered = "";
  let renderTimer: number | null = null;
  let suppressNextScroll = false;

  function strip(content: string): string {
    const m = content.match(/^---\s*\n[\s\S]*?\n---\s*\n?/);
    return m ? content.slice(m[0].length) : content;
  }

  function render(content: string) {
    const body = strip(content);
    const raw = md.render(body);
    rendered = DOMPurify.sanitize(raw);
  }

  $: editorContent, scheduleRender($editorContent);

  function scheduleRender(content: string) {
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = window.setTimeout(() => render(content), 100);
  }

  function onScroll() {
    if (!host) return;
    if (suppressNextScroll) {
      suppressNextScroll = false;
      return;
    }
    const max = host.scrollHeight - host.clientHeight;
    if (max <= 0) return;
    syncScroll.set({ ratio: host.scrollTop / max, source: "preview" });
  }

  const unsubScroll = syncScroll.subscribe((sig) => {
    if (!sig || sig.source === "preview" || !host) return;
    const max = host.scrollHeight - host.clientHeight;
    if (max <= 0) return;
    suppressNextScroll = true;
    host.scrollTop = sig.ratio * max;
  });

  onMount(() => {
    host.addEventListener("scroll", onScroll, { passive: true });
  });

  onDestroy(() => {
    unsubScroll();
    if (renderTimer) clearTimeout(renderTimer);
  });
</script>

<div class="preview" bind:this={host}>
  {#if !$currentFile}
    <p class="empty">Select a file from the tree to start editing.</p>
  {:else}
    <article>{@html rendered}</article>
  {/if}
</div>

<style>
  .preview {
    height: 100%;
    overflow: auto;
    padding: 1.5rem 2rem;
    line-height: 1.55;
    background: var(--bg);
    color: var(--fg);
  }
  .empty {
    color: var(--fg-muted);
    font-style: italic;
  }
  .preview :global(h1) {
    font-size: 1.6em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.3em;
  }
  .preview :global(h2) {
    font-size: 1.3em;
    margin-top: 1.4em;
  }
  .preview :global(code) {
    background: var(--bg-sunken);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 0.9em;
  }
  .preview :global(pre) {
    background: var(--bg-sunken);
    padding: 0.8em 1em;
    border-radius: 4px;
    overflow-x: auto;
  }
  .preview :global(pre code) {
    background: transparent;
    padding: 0;
  }
  .preview :global(a) {
    color: var(--accent);
  }
  .preview :global(blockquote) {
    border-left: 3px solid var(--border);
    padding-left: 1em;
    color: var(--fg-muted);
  }
  .preview :global(table) {
    border-collapse: collapse;
  }
  .preview :global(th),
  .preview :global(td) {
    border: 1px solid var(--border);
    padding: 4px 8px;
  }
</style>
