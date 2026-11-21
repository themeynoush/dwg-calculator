"""Convert node: DWG → DXF with LibreDWG's `dwg2dxf` CLI.

DWG is a closed binary format; Python libraries read DXF only. This is the one
place that knows about the converter — swapping in ODA File Converter means
replacing `_convert_one`.
"""
import logging
import shutil
import subprocess
from pathlib import Path

from src.state import PipelineState

logger = logging.getLogger(__name__)

CONVERTER = "dwg2dxf"
TIMEOUT_S = 120


def _convert_one(dwg: Path, dxf: Path) -> None:
    # dwg2dxf exits non-zero on recoverable warnings too, so trust the output file.
    result = subprocess.run(
        [CONVERTER, "-y", "-o", str(dxf), str(dwg)],
        capture_output=True, text=True, timeout=TIMEOUT_S,
    )
    if not dxf.exists() or dxf.stat().st_size == 0:
        raise RuntimeError(result.stderr.strip()[-300:] or "dwg2dxf produced no output")


def convert(state: PipelineState) -> dict:
    if state.pending and shutil.which(CONVERTER) is None:
        raise RuntimeError(f"'{CONVERTER}' not found. Install LibreDWG: brew install libredwg")

    work_dir = Path(state.output_dir) / "dxf"
    work_dir.mkdir(parents=True, exist_ok=True)

    dxf_paths, errors = {}, dict(state.errors)
    for f in state.pending:
        dxf = work_dir / f"{f.name}.dxf"
        try:
            _convert_one(Path(f.path), dxf)
            dxf_paths[f.name] = str(dxf)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            errors[f.name] = f"convert: {exc}"
            logger.warning("Skipping %s: conversion failed (%s)", f.name, exc)
    return {"dxf_paths": dxf_paths, "errors": errors}
