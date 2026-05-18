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
    <p class="empty"><em>Choose a note from the shelf.</em></p>
  {:else}
    <article class="prose">{@html rendered}</article>
  {/if}
</div>

<style>
  .preview {
    height: 100%;
    overflow: auto;
    padding: 48px 56px 64px;
    background: var(--bg);
    color: var(--fg);
  }
  .empty {
    color: var(--fg-muted);
    font-family: var(--font-serif);
    font-style: italic;
    font-size: 16px;
    text-align: center;
    margin-top: 4em;
  }
  .prose {
    max-width: 64ch;
    margin: 0 auto;
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 16, "wght" 400;
    font-size: 16px;
    line-height: 1.65;
    color: var(--fg);
  }

  /* H1 — title with hairline rule below */
  .prose :global(h1) {
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 144, "wght" 500, "WONK" 1;
    font-size: 2em;
    line-height: 1.15;
    letter-spacing: -0.015em;
    margin: 0 0 0.2em;
    color: var(--fg);
  }
  .prose :global(h1)::after {
    content: "";
    display: block;
    width: 4em;
    height: 1px;
    background: var(--rule);
    margin: 0.4em 0 1.2em;
  }

  /* H2 — small-caps, tracked out, library section feel */
  .prose :global(h2) {
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 14, "wght" 600;
    font-variant: small-caps;
    letter-spacing: 0.08em;
    font-size: 1em;
    margin: 2.4em 0 0.6em;
    color: var(--fg);
  }

  /* H3 — italic, smaller */
  .prose :global(h3) {
    font-family: var(--font-serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 500;
    font-size: 1.05em;
    margin: 1.8em 0 0.4em;
    color: var(--fg);
  }

  /* Drop cap on the first paragraph */
  .prose :global(> p:first-of-type::first-letter),
  .prose :global(> h1 + p::first-letter) {
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 144, "wght" 600, "SOFT" 60;
    font-size: 3.4em;
    float: left;
    line-height: 0.85;
    padding: 0.08em 0.12em 0 0;
    color: var(--accent);
  }

  .prose :global(p) {
    margin: 0 0 1em;
  }

  .prose :global(a) {
    color: var(--accent);
    text-decoration: none;
    border-bottom: 1px solid var(--accent);
    padding-bottom: 1px;
    transition: background 180ms ease;
  }
  .prose :global(a:hover) {
    background: var(--accent-soft);
  }

  .prose :global(em) {
    font-style: italic;
    color: var(--fg);
  }
  .prose :global(strong) {
    font-variation-settings: "opsz" 16, "wght" 700;
  }

  /* Inline code — monospace, restrained */
  .prose :global(code) {
    font-family: var(--font-mono);
    font-size: 0.86em;
    background: var(--bg-sunken);
    padding: 1px 5px;
    border-radius: 1px;
    border: 1px solid var(--border);
  }
  .prose :global(pre) {
    font-family: var(--font-mono);
    background: var(--bg-sunken);
    border: 1px solid var(--border);
    padding: 14px 18px;
    overflow-x: auto;
    margin: 1.2em 0;
    font-size: 0.86em;
    line-height: 1.5;
  }
  .prose :global(pre code) {
    background: transparent;
    border: none;
    padding: 0;
    font-size: 1em;
  }

  /* Blockquote — left ornamental rule */
  .prose :global(blockquote) {
    margin: 1.4em 0;
    padding: 0.2em 0 0.2em 1.2em;
    border-left: 2px solid var(--accent);
    color: var(--fg-muted);
    font-style: italic;
  }

  /* Lists — hanging numerals/bullets */
  .prose :global(ul),
  .prose :global(ol) {
    padding-left: 1.4em;
    margin: 0.8em 0 1em;
  }
  .prose :global(li) {
    margin: 0.25em 0;
  }
  .prose :global(li)::marker {
    color: var(--rule);
  }

  /* Tables — editorial rule lines */
  .prose :global(table) {
    border-collapse: collapse;
    margin: 1.2em 0;
    font-size: 0.94em;
    width: 100%;
  }
  .prose :global(thead) {
    border-bottom: 1.5px solid var(--rule);
  }
  .prose :global(th) {
    font-variation-settings: "opsz" 14, "wght" 600;
    font-variant: small-caps;
    letter-spacing: 0.06em;
    text-align: left;
    padding: 6px 14px 6px 0;
  }
  .prose :global(td) {
    padding: 6px 14px 6px 0;
    border-bottom: 1px solid var(--border);
  }

  /* Horizontal rule — ornamental */
  .prose :global(hr) {
    border: none;
    text-align: center;
    margin: 2.4em 0;
    height: 1em;
  }
  .prose :global(hr)::before {
    content: "❦";
    color: var(--rule);
    font-size: 1em;
  }
</style>
