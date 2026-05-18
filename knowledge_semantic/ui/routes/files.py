"""Routes for browsing, reading, and writing knowledge files."""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from knowledge_semantic.ui.services import kb, tree

router = APIRouter()


class WriteRequest(BaseModel):
    path: str
    content: str


@router.get("/api/tree")
def get_tree():
    return {"root": tree.build_tree()}


@router.get("/api/file")
def get_file(path: str):
    if not tree.is_inside_knowledge(path):
        raise HTTPException(status_code=400, detail="Path is outside the knowledge directory")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "r") as f:
        content = f.read()
    metadata, body = kb.parse(content)
    return {
        "path": path,
        "content": content,
        "body": body,
        "frontmatter": metadata,
        "mtime": os.path.getmtime(path),
    }


@router.put("/api/file")
def put_file(req: WriteRequest):
    if not tree.is_inside_knowledge(req.path):
        raise HTTPException(status_code=400, detail="Path is outside the knowledge directory")
    if not req.path.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are accepted")

    os.makedirs(os.path.dirname(req.path), exist_ok=True)
    tmp = req.path + ".tmp"
    with open(tmp, "w") as f:
        f.write(req.content)
    os.replace(tmp, req.path)

    result = kb.upsert_with_retry(req.path, req.content)

    return {
        "status": "indexed",
        "path": req.path,
        "mtime": os.path.getmtime(req.path),
        "description": result.get("description", ""),
        "category": result.get("category", "uncategorized"),
        "terms_indexed": result.get("terms_indexed", 0),
    }
