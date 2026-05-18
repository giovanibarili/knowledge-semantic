<script lang="ts">
  import { currentFile, dirty, saveStatus, totalIndexed } from "../stores";

  const LABELS = {
    idle: "ready",
    editing: "editing…",
    saving: "saving…",
    indexed: "indexed",
    error: "save failed",
  } as const;
</script>

<footer>
  <span class="indexed">{$totalIndexed} indexed</span>
  <span class="sep">·</span>
  {#if $currentFile}
    <span class="path" title={$currentFile.path}>{$currentFile.path}</span>
    <span class="sep">·</span>
  {/if}
  <span class="status" data-state={$saveStatus} class:dirty={$dirty}>
    {LABELS[$saveStatus]}
  </span>
</footer>

<style>
  footer {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    background: var(--bg-sunken);
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--fg-muted);
  }
  .path {
    color: var(--fg);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 600px;
  }
  .sep {
    color: var(--border);
  }
  .status[data-state="indexed"] {
    color: var(--status-ok);
  }
  .status[data-state="saving"],
  .status[data-state="editing"] {
    color: var(--status-warn);
  }
  .status[data-state="error"] {
    color: var(--status-err);
  }
</style>
