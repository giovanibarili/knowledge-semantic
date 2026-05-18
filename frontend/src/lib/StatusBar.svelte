<script lang="ts">
  import { currentFile, dirty, saveStatus, totalIndexed } from "../stores";

  const LABELS = {
    clean: "ready",
    dirty: "unsaved",
    saving: "filing",
    saved: "filed",
    error: "snag",
  } as const;

  $: shortPath = $currentFile?.path
    ? $currentFile.path.replace(/^.*\/knowledge\//, "")
    : null;

  // Show "unsaved" whenever the buffer is dirty, regardless of saveStatus phase.
  $: displayState = $dirty && $saveStatus !== "saving" ? "dirty" : $saveStatus;
</script>

<footer>
  <span class="left">
    <span class="numeral">№</span><span class="count">{$totalIndexed}</span>
    <span class="label">notes</span>
  </span>

  {#if shortPath}
    <span class="center">
      <em>{shortPath}</em>
    </span>
  {:else}
    <span class="center"></span>
  {/if}

  <span class="right">
    {#if $dirty && $saveStatus !== "saving"}
      <span class="dot" aria-hidden="true">•</span>
    {/if}
    <span class="status" data-state={displayState}>
      {LABELS[displayState]}
    </span>
  </span>
</footer>

<style>
  footer {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: baseline;
    gap: 16px;
    padding: 8px 24px;
    background: var(--bg-elev);
    border-top: 1px solid var(--rule);
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 12, "wght" 400;
    font-size: 12px;
    color: var(--fg-muted);
    position: relative;
  }
  footer::before {
    content: "";
    position: absolute;
    left: 24px;
    right: 24px;
    top: 4px;
    height: 1px;
    background: var(--rule);
    opacity: 0.35;
  }
  .left {
    justify-self: start;
    display: inline-flex;
    align-items: baseline;
    gap: 4px;
  }
  .center {
    justify-self: center;
    color: var(--fg);
    max-width: 60ch;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12.5px;
  }
  .right {
    justify-self: end;
  }
  .numeral {
    color: var(--rule);
    font-style: italic;
    margin-right: 2px;
  }
  .count {
    color: var(--fg);
    font-variation-settings: "opsz" 12, "wght" 600;
    font-variant-numeric: oldstyle-nums;
  }
  .label {
    font-variant: small-caps;
    letter-spacing: 0.08em;
    margin-left: 4px;
  }
  .status {
    font-variant: small-caps;
    letter-spacing: 0.1em;
    font-variation-settings: "opsz" 12, "wght" 500;
  }
  .status[data-state="saved"] {
    color: var(--status-ok);
  }
  .status[data-state="saving"] {
    color: var(--status-warn);
    font-style: italic;
  }
  .status[data-state="dirty"] {
    color: var(--status-warn);
  }
  .status[data-state="error"] {
    color: var(--status-err);
  }
  .dot {
    color: var(--status-warn);
    font-size: 16px;
    line-height: 0;
    margin-right: 2px;
    animation: dot-pulse 1.8s ease-in-out infinite;
  }
  @keyframes dot-pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
</style>
