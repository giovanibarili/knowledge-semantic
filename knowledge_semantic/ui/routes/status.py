"""Status + health routes."""

from fastapi import APIRouter

from knowledge_semantic.ui.services import kb

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"ok": True}


@router.get("/api/status")
def status():
    collection = kb.get_store()._collection
    raw = collection.get(include=["metadatas"])
    metadatas = raw["metadatas"] or []
    last_indexed = ""
    for m in metadatas:
        ts = (m or {}).get("indexed_at", "")
        if ts > last_indexed:
            last_indexed = ts
    return {
        "total_indexed": len(raw["ids"]),
        "last_indexed": last_indexed,
    }
