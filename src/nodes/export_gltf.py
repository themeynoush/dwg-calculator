"""Export node: normalize geometry and write one binary glTF (.glb) per drawing.

Normalization: centre on the origin, scale the largest dimension to 1,
and convert CAD Z-up to glTF Y-up — so the browser needs no per-file tuning.

Faces are split into one mesh per CAD layer, named after the layer, with a PBR
material in the layer colour. Keywords in the layer name pick the finish
(MIRROR → reflective, GLASS → transparent, LED → glowing...), so the viewer can
show and toggle materials.
"""
import logging
from pathlib import Path

import numpy as np
import trimesh

from src.state import Geometry, PipelineState

logger = logging.getLogger(__name__)

# (x, y, z) Z-up → (x, z, -y) Y-up
Z_UP_TO_Y_UP = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)


def normalize(vertices: np.ndarray) -> np.ndarray:
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    size = float((hi - lo).max())
    centred = vertices - (lo + hi) / 2
    scaled = centred / size if size > 0 else centred
    return scaled @ Z_UP_TO_Y_UP.T


DEFAULT_RGB = (184, 196, 208)   # neutral grey-blue for unlayered / white (ACI 7) faces

# first matching keyword wins: (metallic, roughness, opacity, emissive)
FINISHES: list[tuple[tuple[str, ...], tuple[float, float, float, bool]]] = [
    (("MIRROR",), (1.0, 0.02, 1.0, False)),
    (("GLASS",), (0.1, 0.05, 0.3, False)),
    (("LED", "BACKLIT", "LIGHT"), (0.0, 0.5, 1.0, True)),
    (("BRASS", "METAL", "STEEL", "BRONZE"), (0.9, 0.3, 1.0, False)),
    (("LACQUER", "MARBLE", "ONYX", "POLISHED"), (0.0, 0.2, 1.0, False)),
    (("CARPET", "VELVET", "FABRIC", "WALLPAPER"), (0.0, 0.95, 1.0, False)),
]


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material_for(layer: str, rgb: tuple[int, int, int]) -> trimesh.visual.material.PBRMaterial:
    if rgb in ((255, 255, 255), (0, 0, 0)):
        rgb = DEFAULT_RGB
    metallic, roughness, opacity, emissive = 0.05, 0.7, 1.0, False
    upper = layer.upper()
    for keywords, finish in FINISHES:
        if any(k in upper for k in keywords):
            metallic, roughness, opacity, emissive = finish
            break
    color = [_srgb_to_linear(c / 255) for c in rgb]   # glTF colour factors are linear
    return trimesh.visual.material.PBRMaterial(
        name=layer,
        baseColorFactor=[*color, opacity],
        metallicFactor=metallic,
        roughnessFactor=roughness,
        emissiveFactor=color if emissive else None,
        alphaMode="BLEND" if opacity < 1 else None,
        doubleSided=True,
    )


def _layer_meshes(geometry: Geometry, vertices: np.ndarray):
    faces = np.asarray(geometry.faces)
    layers = np.asarray(geometry.face_layers or ["faces"] * len(faces))
    for layer in dict.fromkeys(layers.tolist()):          # keep first-seen order
        used, local = np.unique(faces[layers == layer], return_inverse=True)
        mesh = trimesh.Trimesh(vertices=vertices[used], faces=local.reshape(-1, 3), process=False)
        rgb = geometry.layer_colors.get(layer, DEFAULT_RGB)
        mesh.visual = trimesh.visual.TextureVisuals(material=material_for(layer, rgb))
        yield layer, mesh


def build_scene(geometry: Geometry) -> trimesh.Scene:
    vertices = normalize(np.asarray(geometry.vertices, dtype=float))
    scene = trimesh.Scene()
    if geometry.faces:
        for layer, mesh in _layer_meshes(geometry, vertices):
            scene.add_geometry(mesh, geom_name=layer, node_name=layer)
    if geometry.segments:
        entities = [trimesh.path.entities.Line(list(s)) for s in geometry.segments]
        path = trimesh.path.Path3D(entities=entities, vertices=vertices, process=False)
        scene.add_geometry(path, geom_name="lines")
    return scene


def export_gltf(state: PipelineState) -> dict:
    out = Path(state.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    exported = []
    for name, geometry in state.geometries.items():
        (out / f"{name}.glb").write_bytes(build_scene(geometry).export(file_type="glb"))
        exported.append(name)
    logger.info("Exported %d model(s) to %s", len(exported), out)
    return {"exported": exported}
