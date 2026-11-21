"""Scan node: find DWG files in the uploads folder that need processing."""
import logging
from pathlib import Path

from src.nodes.measure import TAKEOFF_SUFFIX, read_takeoff
from src.state import DwgFile, PipelineState

logger = logging.getLogger(__name__)


def _is_up_to_date(dwg: Path, *outputs: Path) -> bool:
    return all(p.exists() and p.stat().st_mtime >= dwg.stat().st_mtime for p in outputs)


def scan(state: PipelineState) -> dict:
    """List *.dwg files (case-insensitive); skip those with an up-to-date .glb and take-off
    (a take-off saved in an older format counts as out of date)."""
    uploads = Path(state.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    output = Path(state.output_dir)

    pending = []
    for path in sorted(uploads.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".dwg":
            continue
        glb, takeoff = output / f"{path.stem}.glb", output / f"{path.stem}{TAKEOFF_SUFFIX}"
        fresh = _is_up_to_date(path, glb, takeoff) and read_takeoff(takeoff) is not None
        if not state.force and fresh:
            continue
        pending.append(DwgFile(name=path.stem, path=str(path)))
    logger.info("Found %d DWG file(s) to process", len(pending))
    return {"pending": pending}
