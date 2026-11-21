"""Scan node: find DWG files in the uploads folder that need processing."""
import logging
from pathlib import Path

from src.state import DwgFile, PipelineState

logger = logging.getLogger(__name__)


def _is_up_to_date(dwg: Path, glb: Path) -> bool:
    return glb.exists() and glb.stat().st_mtime >= dwg.stat().st_mtime


def scan(state: PipelineState) -> dict:
    """List *.dwg files (case-insensitive); skip those with an up-to-date .glb."""
    uploads = Path(state.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    output = Path(state.output_dir)

    pending = []
    for path in sorted(uploads.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".dwg":
            continue
        if not state.force and _is_up_to_date(path, output / f"{path.stem}.glb"):
            continue
        pending.append(DwgFile(name=path.stem, path=str(path)))
    logger.info("Found %d DWG file(s) to process", len(pending))
    return {"pending": pending}
