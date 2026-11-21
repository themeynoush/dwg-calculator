"""Catalog node: list every viewable model for the sidebar, write catalog.json."""
import json
import logging
from pathlib import Path

from src.state import CatalogEntry, PipelineState

logger = logging.getLogger(__name__)

MODELS_URL = "/models"


def build_catalog(state: PipelineState) -> dict:
    """Includes models from previous runs: a DWG is listed if its .glb exists."""
    uploads, out = Path(state.uploads_dir), Path(state.output_dir)
    catalog = []
    for dwg in sorted(uploads.iterdir(), key=lambda p: p.name.lower()):
        glb = out / f"{dwg.stem}.glb"
        if dwg.suffix.lower() != ".dwg" or not glb.exists():
            continue
        catalog.append(CatalogEntry(
            name=dwg.stem,
            # ?v= busts the browser cache when a model is regenerated
            model_url=f"{MODELS_URL}/{glb.name}?v={int(glb.stat().st_mtime)}",
            source=dwg.name,
            size_bytes=dwg.stat().st_size,
        ))
    payload = {
        "models": [e.model_dump() for e in catalog],
        "errors": state.errors,
    }
    (out / "catalog.json").write_text(json.dumps(payload, indent=2))
    logger.info("Catalog: %d model(s), %d error(s)", len(catalog), len(state.errors))
    return {"catalog": catalog}
