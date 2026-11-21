"""Web server: serves the viewer page, the catalog and the .glb models."""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import pipeline

ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "output"
STATIC_DIR = ROOT / "static"


def create_app(uploads_dir: Path = UPLOADS_DIR, output_dir: Path = OUTPUT_DIR) -> FastAPI:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="DWG 3D Viewer")

    def read_catalog() -> dict:
        path = output_dir / "catalog.json"
        return json.loads(path.read_text()) if path.exists() else {"models": [], "errors": {}}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/catalog")
    def catalog() -> dict:
        return read_catalog()

    @app.post("/api/refresh")
    async def refresh() -> dict:
        await run_in_threadpool(pipeline.run_pipeline, str(uploads_dir), str(output_dir))
        return read_catalog()

    app.mount("/models", StaticFiles(directory=output_dir), name="models")
    return app
