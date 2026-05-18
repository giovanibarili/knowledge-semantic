export type TreeNode = {
  path: string;
  name: string;
  isDir: boolean;
  category: string | null;
  children?: TreeNode[];
};

export type FileResponse = {
  path: string;
  content: string;
  body: string;
  frontmatter: Record<string, unknown> | null;
  mtime: number;
};

export type MapPoint = {
  path: string;
  title: string;
  category: string;
  x: number;
  y: number;
};

export type MapResponse = {
  embedding_hash: string;
  generated_at: number;
  method: string;
  points: MapPoint[];
};

async function jsonOrThrow(res: Response) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

export async function getTree(): Promise<{ root: TreeNode }> {
  return jsonOrThrow(await fetch("/api/tree"));
}

export async function getFile(path: string): Promise<FileResponse> {
  const q = new URLSearchParams({ path });
  return jsonOrThrow(await fetch(`/api/file?${q}`));
}

export async function putFile(path: string, content: string) {
  return jsonOrThrow(
    await fetch("/api/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }),
  );
}

export async function getMap(): Promise<MapResponse> {
  return jsonOrThrow(await fetch("/api/map"));
}

export async function recomputeMap(): Promise<MapResponse> {
  return jsonOrThrow(await fetch("/api/map/recompute", { method: "POST" }));
}

export async function getStatus() {
  return jsonOrThrow(await fetch("/api/status"));
}
