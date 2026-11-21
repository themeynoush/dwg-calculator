import numpy as np
import trimesh

from src.nodes.export_gltf import export_gltf, normalize
from src.state import Geometry, PipelineState


def test_normalize_centres_scales_and_turns_z_up_into_y_up():
    v = normalize(np.array([[0, 0, 0], [4, 2, 10]], dtype=float))
    assert np.allclose(v.min(axis=0) + v.max(axis=0), 0)     # centred
    assert np.isclose((v.max(axis=0) - v.min(axis=0)).max(), 1)
    assert np.isclose(v[:, 1].ptp() if hasattr(v, "ptp") else np.ptp(v[:, 1]), 1)  # Z → Y


def test_export_writes_loadable_glb(tmp_path):
    g = Geometry(vertices=[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 0, 1)],
                 faces=[(0, 1, 2)], segments=[(0, 3)])
    state = PipelineState(uploads_dir=".", output_dir=str(tmp_path), geometries={"m": g})
    assert export_gltf(state)["exported"] == ["m"]
    scene = trimesh.load(tmp_path / "m.glb")
    kinds = {type(x).__name__ for x in scene.geometry.values()}
    assert kinds == {"Trimesh", "Path3D"}


def test_one_mesh_per_layer_with_material_finish(tmp_path):
    g = Geometry(vertices=[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 0, 1)],
                 faces=[(0, 1, 2), (0, 2, 3)], face_layers=["WALL-MIRROR", "FLOOR-OAK"],
                 layer_colors={"WALL-MIRROR": (200, 200, 220), "FLOOR-OAK": (170, 120, 60)})
    state = PipelineState(uploads_dir=".", output_dir=str(tmp_path), geometries={"m": g})
    export_gltf(state)
    scene = trimesh.load(tmp_path / "m.glb")
    materials = {m.visual.material.name: m.visual.material for m in scene.geometry.values()}
    assert set(materials) == {"WALL-MIRROR", "FLOOR-OAK"}
    assert materials["WALL-MIRROR"].metallicFactor == 1.0       # keyword → mirror finish
    # CAD colours are sRGB; glTF stores linear: sRGB 170/120/60 → linear ≈ 0.402/0.188/0.045
    assert np.allclose(materials["FLOOR-OAK"].baseColorFactor[:3] / 255,
                       [0.402, 0.188, 0.045], atol=0.01)
