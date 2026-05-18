import { writable } from "svelte/store";
import type { FileResponse, TreeNode } from "./api";

export const treeRoot = writable<TreeNode | null>(null);
export const currentFile = writable<FileResponse | null>(null);
export const editorContent = writable<string>("");
export const dirty = writable<boolean>(false);

export type SaveStatus = "idle" | "editing" | "saving" | "indexed" | "error";
export const saveStatus = writable<SaveStatus>("idle");

export const totalIndexed = writable<number>(0);

export type Theme = "light" | "dark";
const initialTheme: Theme =
  (typeof localStorage !== "undefined" && (localStorage.getItem("kb-theme") as Theme | null)) ||
  (typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light");

export const theme = writable<Theme>(initialTheme);
theme.subscribe((t) => {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = t;
  }
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("kb-theme", t);
  }
});

const initialTree: boolean =
  typeof localStorage !== "undefined" ? localStorage.getItem("kb-tree") !== "0" : true;
export const treeOpen = writable<boolean>(initialTree);
treeOpen.subscribe((v) => {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("kb-tree", v ? "1" : "0");
  }
});

// Lifted scroll-sync ratio: 0..1 normalized scroll position emitted by editor
// or preview; the other pane listens and mirrors. `source` prevents echo loops.
export type ScrollSignal = { ratio: number; source: "editor" | "preview" };
export const syncScroll = writable<ScrollSignal | null>(null);
