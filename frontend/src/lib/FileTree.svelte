<script lang="ts">
  import type { TreeNode } from "../api";
  import { currentFile } from "../stores";

  export let node: TreeNode;
  export let depth = 0;
  export let openFile: (path: string) => Promise<void>;

  let expanded = depth < 2;

  function toggle() {
    expanded = !expanded;
  }

  function trimMd(name: string) {
    return name.replace(/\.md$/, "");
  }
</script>

<ul class="tree" class:root={depth === 0} class:category={depth === 1}>
  {#if node.isDir && depth > 0}
    <li class="dir-li">
      <button class="dir" on:click={toggle}>
        <span class="caret" aria-hidden="true">{expanded ? "—" : "+"}</span>
        <span class="dir-name">{node.name}</span>
      </button>
      {#if expanded && node.children}
        {#each node.children as child (child.path)}
          <svelte:self node={child} depth={depth + 1} {openFile} />
        {/each}
      {/if}
    </li>
  {:else if node.isDir}
    {#each node.children || [] as child (child.path)}
      <svelte:self node={child} depth={depth + 1} {openFile} />
    {/each}
  {:else}
    <li>
      <button
        class="file"
        class:active={$currentFile?.path === node.path}
        on:click={() => openFile(node.path)}
        title={node.path}
      >
        {trimMd(node.name)}
      </button>
    </li>
  {/if}
</ul>

<style>
  .tree {
    list-style: none;
    padding-left: 0;
    margin: 0;
  }
  .tree:not(.root):not(.category) {
    padding-left: 14px;
    border-left: 1px solid var(--border);
    margin-left: 4px;
  }
  button {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 3px 6px 3px 4px;
    font: inherit;
    text-align: left;
    width: 100%;
    border-radius: 1px;
    transition: background 140ms ease, color 140ms ease;
  }
  button:hover {
    background: var(--accent-soft);
  }

  .dir {
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 14, "wght" 600;
    font-variant: small-caps;
    letter-spacing: 0.09em;
    color: var(--fg);
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding-top: 12px;
    padding-bottom: 4px;
  }
  .dir-li:not(:first-child) .dir {
    border-top: 1px solid var(--border);
    margin-top: 6px;
  }
  .caret {
    font-family: var(--font-mono);
    font-size: 11px;
    width: 10px;
    color: var(--fg-muted);
    display: inline-block;
    text-align: center;
  }
  .dir-name {
    flex: 1;
  }

  .file {
    font-family: var(--font-serif);
    font-variation-settings: "opsz" 14, "wght" 400;
    color: var(--fg);
    padding-left: 22px;
    font-size: 13.5px;
    line-height: 1.5;
    position: relative;
  }
  .file::before {
    content: "·";
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--rule);
  }
  .file.active {
    color: var(--accent);
    background: var(--accent-soft);
    font-style: italic;
  }
  .file.active::before {
    content: "▸";
    color: var(--accent);
    font-size: 9px;
  }
</style>
