<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { EditorState } from "@codemirror/state";
  import { EditorView, lineNumbers, keymap } from "@codemirror/view";
  import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
  import { markdown } from "@codemirror/lang-markdown";
  import {
    currentFile,
    dirty,
    editorContent,
    syncScroll,
  } from "../stores";

  let host: HTMLDivElement;
  let view: EditorView | null = null;
  let currentPath: string | null = null;
  let suppressNextScroll = false;

  function onScroll() {
    if (!view) return;
    if (suppressNextScroll) {
      suppressNextScroll = false;
      return;
    }
    const scroller = view.scrollDOM;
    const max = scroller.scrollHeight - scroller.clientHeight;
    if (max <= 0) return;
    syncScroll.set({ ratio: scroller.scrollTop / max, source: "editor" });
  }

  function buildState(initial: string) {
    return EditorState.create({
      doc: initial,
      extensions: [
        lineNumbers(),
        history(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        markdown(),
        EditorView.lineWrapping,
        EditorView.updateListener.of((u) => {
          if (u.docChanged) {
            const doc = u.state.doc.toString();
            editorContent.set(doc);
            dirty.set(true);
          }
        }),
        EditorView.domEventHandlers({ scroll: onScroll }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "13.5px", background: "var(--bg-sunken)" },
          ".cm-scroller": {
            fontFamily: "var(--font-mono)",
            lineHeight: "1.6",
            padding: "32px 28px",
          },
          ".cm-content": { color: "var(--fg)", caretColor: "var(--accent)" },
          ".cm-cursor": { borderLeftColor: "var(--accent)", borderLeftWidth: "1.5px" },
          ".cm-gutters": {
            background: "var(--bg-sunken)",
            color: "var(--fg-muted)",
            border: "none",
            fontFamily: "var(--font-mono)",
            paddingRight: "12px",
          },
          ".cm-gutterElement": { padding: "0 4px 0 6px" },
          ".cm-activeLine": { background: "transparent" },
          ".cm-activeLineGutter": { background: "transparent", color: "var(--accent)" },
          ".cm-selectionBackground, ::selection": { background: "var(--accent-soft) !important" },
          ".cm-line": { padding: "0 2px" },
        }),
      ],
    });
  }

  const unsubFile = currentFile.subscribe((file) => {
    if (!file || !view) return;
    if (file.path === currentPath) return;
    currentPath = file.path;
    view.setState(buildState(file.content));
    editorContent.set(file.content);
    dirty.set(false);
  });

  const unsubScroll = syncScroll.subscribe((sig) => {
    if (!sig || sig.source === "editor" || !view) return;
    const scroller = view.scrollDOM;
    const max = scroller.scrollHeight - scroller.clientHeight;
    if (max <= 0) return;
    suppressNextScroll = true;
    scroller.scrollTop = sig.ratio * max;
  });

  onMount(() => {
    view = new EditorView({ state: buildState(""), parent: host });
  });

  onDestroy(() => {
    unsubFile();
    unsubScroll();
    view?.destroy();
  });
</script>

<div class="editor" bind:this={host}></div>

<style>
  .editor {
    height: 100%;
    overflow: hidden;
    background: var(--bg-sunken);
  }
  .editor :global(.cm-editor) {
    height: 100%;
  }
  .editor :global(.cm-editor.cm-focused) {
    outline: none;
  }
</style>
