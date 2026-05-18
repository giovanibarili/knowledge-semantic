<script lang="ts">
  import type { TreeNode } from "../api";
  import { currentFile } from "../stores";
  import { getFile } from "../api";

  export let node: TreeNode;
  export let depth = 0;

  let expanded = depth < 2;

  async function open(path: string) {
    const file = await getFile(path);
    currentFile.set(file);
  }

  function toggle() {
    expanded = !expanded;
  }
</script>

<ul class="tree" class:root={depth === 0}>
  {#if node.isDir && depth > 0}
    <li>
      <button class="dir" on:click={toggle}>
        <span class="caret">{expanded ? "▾" : "▸"}</span>
        {node.name}
      </button>
      {#if expanded && node.children}
        {#each node.children as child (child.path)}
          <svelte:self node={child} depth={depth + 1} />
        {/each}
      {/if}
    </li>
  {:else if node.isDir}
    {#each node.children || [] as child (child.path)}
      <svelte:self node={child} depth={depth + 1} />
    {/each}
  {:else}
    <li>
      <button
        class="file"
        class:active={$currentFile?.path === node.path}
        on:click={() => open(node.path)}
        title={node.path}
      >
        {node.name}
      </button>
    </li>
  {/if}
</ul>

<style>
  .tree {
    list-style: none;
    padding-left: 0.75rem;
    margin: 0;
  }
  .tree.root {
    padding-left: 0;
  }
  button {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 2px 4px;
    font: inherit;
    text-align: left;
    width: 100%;
    border-radius: 3px;
  }
  button:hover {
    background: var(--bg-sunken);
  }
  .dir {
    font-weight: 600;
  }
  .caret {
    display: inline-block;
    width: 1em;
    color: var(--fg-muted);
  }
  .file {
    color: var(--fg);
  }
  .file.active {
    background: var(--bg-sunken);
    color: var(--accent);
  }
</style>
