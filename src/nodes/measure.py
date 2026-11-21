"""Measure node: per-material take-off (L, W, H, surface) in metres.

Runs on the raw CAD geometry (before export normalizes it), converts drawing
units ($INSUNITS) to metres, and writes `<name>.takeoff.json` next to the .glb
so unchanged drawings keep their quantities without being reprocessed.

Dimensions come from the bounding box of all faces on the material's layer:
- L (length) = longer horizontal side, W (width) = shorter horizontal side,
  H (height) = vertical side;
- surface = L x W (plan area; H is shown but not used for the surface).
"""
import json
import logging
from pathlib import Path

import numpy as np
from ezdxf import units
from pydantic import ValidationError

from src.state import Geometry, MaterialQuantity, PipelineState

logger = logging.getLogger(__name__)

UNITLESS_AS = units.M   # drawings without $INSUNITS are read as metres
TAKEOFF_SUFFIX = ".takeoff.json"


def to_metres(insunits: int) -> float:
    try:
        source = units.InsertUnits(insunits or UNITLESS_AS)
    except ValueError:              # out-of-range $INSUNITS: treat as unitless
        source = units.InsertUnits(UNITLESS_AS)
    return units.conversion_factor(source, units.InsertUnits.Meters)


def read_takeoff(path: Path) -> list[MaterialQuantity] | None:
    """Saved take-off, or None if missing / unreadable / from an older format."""
    try:
        return [MaterialQuantity(**q) for q in json.loads(path.read_text())]
    except (OSError, ValueError, TypeError, ValidationError):
        return None


def takeoff(geometry: Geometry, scale: float) -> list[MaterialQuantity]:
    if not geometry.faces:
        return []
    vertices = np.asarray(geometry.vertices, dtype=float) * scale
    faces = np.asarray(geometry.faces)
    layers = np.asarray(geometry.face_layers or ["faces"] * len(faces))
    result = []
    for layer in sorted(set(layers.tolist())):
        layer_faces = faces[layers == layer]
        pts = vertices[np.unique(layer_faces)]
        dx, dy, dz = (float(v) for v in pts.max(axis=0) - pts.min(axis=0))
        length, width = max(dx, dy), min(dx, dy)
        result.append(MaterialQuantity(
            layer=layer,
            length_m=round(length, 3),
            width_m=round(width, 3),
            height_m=round(dz, 3),
            area_m2=round(length * width, 3),
        ))
    return result


def measure(state: PipelineState) -> dict:
    out = Path(state.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    quantities = {}
    for name, geometry in state.geometries.items():
        doc = state.documents.get(name)
        scale = to_metres(doc.units if doc is not None else 0)
        quantities[name] = takeoff(geometry, scale)
        (out / f"{name}{TAKEOFF_SUFFIX}").write_text(
            json.dumps([q.model_dump() for q in quantities[name]], indent=2))
        logger.info("%s: measured %d material(s)", name, len(quantities[name]))
    return {"quantities": quantities}
