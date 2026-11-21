import ezdxf

from src.nodes.extract_geometry import extract_geometry
from src.state import PipelineState
from tests.conftest import make_doc


def _run(**docs):
    state = PipelineState(uploads_dir=".", output_dir=".", documents=docs)
    return extract_geometry(state)


def test_cube_faces_become_triangles_and_lines_segments():
    g = _run(cube=make_doc())["geometries"]["cube"]
    assert len(g.faces) == 12
    assert len(g.segments) == 1


def test_block_references_are_expanded():
    g = _run(d=make_doc(cube=False, line=False, insert=True))["geometries"]["d"]
    zs = [v[2] for v in g.vertices]
    assert len(g.segments) == 1 and max(zs) == 3
    assert g.vertices[0][:2] == (5, 5)    # moved to the insertion point


def test_text_is_skipped_and_empty_drawing_is_an_error():
    result = _run(t=make_doc(cube=False, line=False, text=True), empty=ezdxf.new())
    assert result["geometries"] == {}
    assert set(result["errors"]) == {"t", "empty"}


def test_faces_keep_their_layer_and_layer_colour():
    doc = ezdxf.new()
    doc.layers.add("WALL-MIRROR", color=5)                       # ACI 5 = blue
    msp = doc.modelspace()
    quad = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    msp.add_3dface(quad, dxfattribs={"layer": "WALL-MIRROR"})
    msp.add_3dface([(0, 0, 1), (1, 0, 1), (1, 1, 1)], dxfattribs={"layer": "FLOOR", "color": 1})
    g = _run(d=doc)["geometries"]["d"]
    assert g.face_layers == ["WALL-MIRROR", "WALL-MIRROR", "FLOOR"]
    assert g.layer_colors == {"WALL-MIRROR": (0, 0, 255), "FLOOR": (255, 0, 0)}
