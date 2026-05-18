<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { EditorState } from "@codemirror/state";
  import { EditorView, lineNumbers, keymap } from "@codemirror/view";
  import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
  import { markdown } from "@codemirror/lang-markdown";
  import { putFile } from "../api";
  import {
    currentFile,
    dirty,
    editorContent,
    saveStatus,
    syncScroll,
    theme,
  } from "../stores";

  let host: HTMLDivElement;
  let view: EditorView | null = null;
  let saveTimer: number | null = null;
  let currentPath: string | null = null;
  let suppressNextScroll = false;

  function scheduleSave(content: string) {
    if (saveTimer) clearTimeout(saveTimer);
    saveStatus.set("editing");
    saveTimer = window.setTimeout(() => doSave(content), 1000);
  }

  async function doSave(content: string) {
    if (!currentPath) return;
    saveStatus.set("saving");
    try {
      await putFile(currentPath, content);
      dirty.set(false);
      saveStatus.set("indexed");
    } catch (e) {
      console.error(e);
      saveStatus.set("error");
    }
  }

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
            scheduleSave(doc);
          }
        }),
        EditorView.domEventHandlers({ scroll: onScroll }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "13px", background: "var(--bg)" },
          ".cm-scroller": { fontFamily: "ui-monospace, Menlo, monospace" },
          ".cm-content": { color: "var(--fg)" },
          ".cm-gutters": { background: "var(--bg-sunken)", color: "var(--fg-muted)", border: "none" },
          ".cm-activeLine": { background: "transparent" },
          ".cm-activeLineGutter": { background: "transparent" },
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
    saveStatus.set("idle");
  });

  const unsubScroll = syncScroll.subscribe((sig) => {
    if (!sig || sig.source === "editor" || !view) return;
    const scroller = view.scrollDOM;
    const max = scroller.scrollHeight - scroller.clientHeight;
    if (max <= 0) return;
    suppressNextScroll = true;
    scroller.scrollTop = sig.ratio * max;
  });

  // Re-theme on theme change — CodeMirror picks up CSS vars automatically.
  const unsubTheme = theme.subscribe(() => {});

  onMount(() => {
    view = new EditorView({ state: buildState(""), parent: host });
  });

  onDestroy(() => {
    unsubFile();
    unsubScroll();
    unsubTheme();
    view?.destroy();
    if (saveTimer) clearTimeout(saveTimer);
  });
</script>

<div class="editor" bind:this={host}></div>

<style>
  .editor {
    height: 100%;
    overflow: hidden;
    background: var(--bg);
  }
  .editor :global(.cm-editor) {
    height: 100%;
  }
  .editor :global(.cm-editor.cm-focused) {
    outline: none;
  }
</style>
