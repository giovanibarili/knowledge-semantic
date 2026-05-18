"""FastAPI app factory."""

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from knowledge_semantic.ui.routes import files, status


def create_app():
    app = FastAPI(title="Knowledge Semantic UI")

    app.include_router(status.router)
    app.include_router(files.router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets"),
                                         check_dir=False), name="assets")

        @app.get("/")
        def index():
            return FileResponse(os.path.join(static_dir, "index.html"))

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            # Serve index.html for unknown paths so the SPA can handle routing.
            target = os.path.join(static_dir, full_path)
            if os.path.isfile(target):
                return FileResponse(target)
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app
